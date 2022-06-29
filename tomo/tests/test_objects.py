# **************************************************************************
# *
# * Authors:     Pablo Conesa (pconesa@cnb.csic.es) [1]
# *
# * [1] Unidad de Bioinformatica of Centro Nacional de Biotecnologia, CSIC
# *
# * This program is free software; you can redistribute it and/or modify
# * it under the terms of the GNU General Public License as published by
# * the Free Software Foundation; either version 2 of the License, or
# * (at your option) any later version.
# *
# * This program is distributed in the hope that it will be useful,
# * but WITHOUT ANY WARRANTY; without even the implied warranty of
# * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# * GNU General Public License for more details.
# *
# * You should have received a copy of the GNU General Public License
# * along with this program; if not, write to the Free Software
# * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA
# * 02111-1307  USA
# *
# *  All comments concerning this program package may be sent to the
# *  e-mail address 'scipion@cnb.csic.es'
# *
# **************************************************************************
from pyworkflow.tests import BaseTest
from tomo.constants import SCIPION
from tomo.objects import SetOfTiltSeriesCoordinates, TiltSeriesCoordinate, SetOfSubTomograms, SetOfTomograms, Tomogram, \
    SetOfCoordinates3D, Coordinate3D, SubTomogram

MYTSID = "MYTSID"

SAMPLING_RATE = 10

Z_VALUE = 30

Y_VALUE = 20

X_VALUE = 10


class TestTomoModel(BaseTest):
    """ This class check if the Object model behaves as expected"""

    @classmethod
    def setUpClass(cls):
        cls.setupTestOutput()

    def test_set_of_tilt_series_coordinates(self):
        """ Tests the SetOfTiltSeries model"""

        tsCoord = TiltSeriesCoordinate()

        tsCoord.setX(X_VALUE)
        tsCoord.setY(Y_VALUE)
        tsCoord.setZ(Z_VALUE)

        self.assertEqual(X_VALUE, tsCoord.getX(), "X is wrong")
        self.assertEqual(Y_VALUE, tsCoord.getY(), "Y is wrong")
        self.assertEqual(Z_VALUE, tsCoord.getZ(), "Z is wrong")

        posAngs = tsCoord.getPosition()
        self.assertEqual(X_VALUE, posAngs[0], "X is wrong")
        self.assertEqual(Y_VALUE, posAngs[1], "Y is wrong")
        self.assertEqual(Z_VALUE, posAngs[2], "Z is wrong")

        posPixels = tsCoord.getPosition(sampling_rate=SAMPLING_RATE)
        self.assertEqual(X_VALUE / SAMPLING_RATE, posPixels[0], "X is wrong in pixels")
        self.assertEqual(Y_VALUE / SAMPLING_RATE, posPixels[1], "Y is wrong in pixels")
        self.assertEqual(Z_VALUE / SAMPLING_RATE, posPixels[2], "Z is wrong in pixels")

        tsCoord.setPosition(X_VALUE/SAMPLING_RATE, Y_VALUE/SAMPLING_RATE, Z_VALUE/SAMPLING_RATE, sampling_rate=SAMPLING_RATE)
        posAngs = tsCoord.getPosition()
        self.assertEqual(X_VALUE, posAngs[0], "X is wrong when set with sampling rate")
        self.assertEqual(Y_VALUE, posAngs[1], "Y is wrong when set with sampling rate")
        self.assertEqual(Z_VALUE, posAngs[2], "Z is wrong when set with sampling rate")

        tsCoord.setTsId(MYTSID)
        self.assertEqual(MYTSID, tsCoord.getTsId(), "TSID is wrong")



        set = SetOfTiltSeriesCoordinates.create(self.outputPath)
        set.append(tsCoord)

        for tsCoord in set:
            posAngs = tsCoord.getPosition()
            self.assertEqual(X_VALUE, posAngs[0], "X is wrong when set with sampling rate")
            self.assertEqual(Y_VALUE, posAngs[1], "Y is wrong when set with sampling rate")
            self.assertEqual(Z_VALUE, posAngs[2], "Z is wrong when set with sampling rate")
            self.assertEqual(MYTSID, tsCoord.getTsId(), "TSID is wrong")


    def test_set_of_subtomograms(self):
        """ Tests the SetOfSubtomograms model"""

        # Create tomograms set
        tomos = SetOfTomograms.create(self.outputPath)

        tomo1 = Tomogram()
        tomo1.setTsId("TS_1")
        tomos.append(tomo1)

        tomo2 = Tomogram()
        tomo2.setTsId("TS_2")
        tomos.append(tomo2)

        # Create Coordinates set with just one coordinate pointing to just one tomogram
        coords = SetOfCoordinates3D.create(self.outputPath)

        coord1 = Coordinate3D()
        coord1.setX(0,SCIPION)
        coord1.setY(0, SCIPION)
        coord1.setZ(0, SCIPION)
        coord1.setTomoId("TS_1")
        coords.append(coord1)

        coords.setPrecedents(tomos)

        coords.write()

        # Test precedents involved
        self.assertEqual(len(coords.getPrecedentsInvolved()), 1, "getPrecedentsInvolved does not seem to work")


        subtomos = SetOfSubTomograms.create(self.outputPath)
        subtomos.setCoordinates3D(coords)

        subtomo = SubTomogram()
        subtomo.setCoordinate3D(coord1)
        subtomos.append(subtomo)

        subtomos.write()

        self.assertEqual(len(subtomos.getTomograms()), 1, "getTomograms does not return the right element count")





