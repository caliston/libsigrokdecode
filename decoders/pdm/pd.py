##
## This file is part of the libsigrokdecode project.
##
## Copyright (C) 2019 Benedikt Otto <benedikt_o@web.de>
## Copyright (C) 2023 A. Theodore Markettos <git@markettos.org.uk>
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, see <http://www.gnu.org/licenses/>.
##

import sigrokdecode as srd

class ChannelError(Exception):
    pass

class Decoder(srd.Decoder):
    api_version = 3
    id = 'pdm'
    name = 'PDM'
    longname = 'Pulse distance modulation'
    desc = 'Pulse distance modulation'
    license = 'gplv2+'
    inputs = ['logic']
    outputs = []
    tags = ['Encoding']
    channels = (
        {'id': 'D', 'name': 'D', 'desc': 'Data input'},
    )
    options = (
        {'id': 'polarity', 'desc': 'Expected polarity',
            'default': 'active-low', 'values': ('active-high', 'active-low')},
        {'id': 'zerotime', 'desc': 'Time for zero bit (us)',
            'default': 400},
        {'id': 'onetime', 'desc': 'Time for one bit (us)',
            'default': 800},
        {'id': 'tolerance', 'desc': 'Tolerance (%)',
            'default': 20},
        {'id': 'endian', 'desc': 'Endianness',
            'default': 'little', 'values': ('little', 'big')},
    )
    annotations = (
        ('bit', 'Bit'),
        ('leader', 'Leader'),
        ('hex', 'Hex'),
        ('word', 'Word'),
    )
    annotation_rows = (
        ('bits', 'Decoded bits', (0,1)),
        ('hexdigits', 'Hex digits', (2,)),
        ('hexword', 'Word', (3,)),
    )

    def __init__(self):
        self.reset()

    def reset(self):
        self.nybble = 0
        self.hex_bits = 0
        self.starthex = 0
        self.group = 0
        self.group_bits = 0
        self.startgroup = 0

    def start(self):
        self.out_ann = self.register(srd.OUTPUT_ANN)

    def metadata(self, key, value):
        if key == srd.SRD_CONF_SAMPLERATE:
            self.samplerate = value


    def putb(self, ss_block, es_block, data):
        self.put(ss_block, es_block, self.out_ann, data)


    # Calculate timing thresholds, using the tolerance provided
    # Each are towards the middle of the range, ie
    # zero_samples is calculated from zero_time+tolerance and
    # one_samples from one_time-tolerance
    def calc_rate(self):
        if self.options['tolerance']:
            self.tolerance = self.options['tolerance']/100.0
        else:
            self.tolerance = 0
        if self.options['zero_time']:
            self.zero_samples = int(self.samplerate * float(self.options['zero_time']) * (1+self.tolerance) / 1000000) + 1
        else:
            self.zero_samples = 0
        if self.options['one_time']:
            self.one_samples = int(self.samplerate * float(self.options['one_time']) * (1-self.tolerance) / 1000000) - 1
        else:
            self.one_samples = 0

    # Build up hex digits and words.  Label the signal with hex digits
    def addhex(self, bit, currentpos):
        if self.options['endian'] == 'little':
            self.nybble = (self.nybble << 1) | bit
            self.group = (self.group << 1) | bit
        else:
            self.nybble |= bit << self.hex_bits
            self.group |= bit << self.group_bits
        self.hex_bits += 1
        self.group_bits += 1
        if (self.hex_bits == 4):
                self.putb(self.starthex, currentpos, [2, [hex(self.nybble)[2:]]])
                self.starthex = currentpos
                self.hex_bits = 0
                self.nybble = 0

    def decode(self):
        if not self.samplerate:
            raise SamplerateError('Cannot decode without samplerate.')
        self.calc_rate()

        oldpin = self.wait()[0]
        lastpos = self.samplenum
        falling = lastpos
        lastfalling = falling
        rising = lastpos
        lastrising = lastpos
        lastlastpos = lastpos
        highwidth = 0
        lowwidth = 0
        value = ''
        conditions = [{0: 'e'}]

        while True:
            # Wait for any change.
            pintuple = self.wait(conditions)
            currentpos = self.samplenum

            # Invert the input if set as active low
            # from hereon everything is active high
            if self.options['polarity'] == 'active-low':
                pin = 1-pintuple[0]
            else:
                pin = pintuple[0]

            edge = ''
            
            # Measure timing of low and high periods
            if pin == 0 and oldpin == 1:
                edge = 'f'
                lastfalling = falling
                falling = currentpos
                highwidth = falling - rising
            elif pin == 1 and oldpin == 0:
                edge = 'r'
                lastrising = rising
                rising = currentpos
                lowwidth = rising - falling

            else:
                pass

            width = currentpos - lastpos
            value = ''

            # Measure timing when input is off/low
            # Decide if the bit is a zero or a one based on the
            # length of the low period and the timing parameters
            # provided
            if edge == 'r' and lowwidth > self.zero_samples and lowwidth <= self.one_samples*1.5 and highwidth <= self.one_samples*2:
                value = 1
                self.putb(lastrising, rising, [0, [str(value)]])
                self.addhex(value, currentpos)
            elif edge == 'r' and lowwidth < self.zero_samples:
                value = 0
                self.putb(lastrising, rising, [0, [str(value)]])
                self.addhex(value, currentpos)

            # Measure the times when the signal is active/high
            # and label as leadin and leadout periods
            # At present a crude measurement of 'much longer than a one' is used
            if edge == 'f' and (highwidth >= self.one_samples * 2) and (lowwidth >= self.zero_samples * 20) and (lowwidth < self.zero_samples * 100):
                value = 'leadout'
                self.putb(rising, falling, [0, [value]])
                # as we've concluded, label the full hex word
                self.putb(self.startgroup, currentpos, [3, [hex(self.group)]])
            elif edge == 'f' and (highwidth >= self.one_samples * 2):
                value = 'leadin'
                self.putb(rising, falling, [0, [value]])
                self.starthex = falling
                self.startgroup = falling
                self.group_bits = 0
                self.group = 0

            oldpin = pin
            lastlastpos = lastpos
            lastpos = currentpos
