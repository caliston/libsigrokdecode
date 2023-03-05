##
## This file is part of the libsigrokdecode project.
##
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

'''
This decoder decodes Pulse Distance Modulation.

PDM conveys bit information based on different 'off' times of an alternating
signal, sometimes on a modulated carrier (which this decoder does not
demodulate).  For example, a signal might be 'on'/high for 400us and then
'off'/low for a length of time in which 400us repesents a zero and 800us
represents a one.  Such signals typically have a leadin 'high'/ period or

PDM is the basis of the infrared remote control protocols such as NEC, but
is more generic than that.  This decoder allows arbitrary adjustment of bit
timing as variation may occur even within the same bidirectional
communication.

Bits, decoded hex digits and arbitrary-length hex words are output.
'''

from .pd import Decoder
