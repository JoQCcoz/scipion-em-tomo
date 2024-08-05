# *
# * Authors:     Scipion Team
# *
# * Unidad de  Bioinformatica of Centro Nacional de Biotecnologia , CSIC
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
# *  e-mail address 'scipion-users@lists.sourceforge.net'
# *
# **************************************************************************
from imod.constants import OUTPUT_TILTSERIES_NAME
from imod.protocols import ProtImodTsNormalization, ProtImodImportTransformationMatrix
from pwem import ALIGN_2D
from pwem.protocols import ProtUnionSet
from pyworkflow.tests import setupTestProject, DataSet
from pyworkflow.utils import magentaStr
from tomo.protocols import ProtImportTs, ProtImportTomograms
from tomo.protocols.protocol_import_tomograms import OUTPUT_NAME
from tomo.tests import RE4_STA_TUTO, DataSetRe4STATuto
from tomo.tests.test_base_centralized_layer import TestBaseCentralizedLayer

TS_01 = 'TS_01'
TS_03 = 'TS_03'
TS_43 = 'TS_43'
TS_45 = 'TS_45'
TS_54 = 'TS_54'
tsDims40 = [3710, 3838, 40]
tsDims41 = [3710, 3838, 41]
tomoDimsThk300 = [928, 928, 300]
tomoDimsThk280 = [928, 928, 280]
tomoDimsThk340 = [928, 928, 340]


class TestJoinTomoSets(TestBaseCentralizedLayer):
    ds = None
    bin4 = 4
    bin4SRate = DataSetRe4STATuto.unbinnedPixSize.value * 4

    @classmethod
    def setUpClass(cls):
        setupTestProject(cls)
        cls.ds = DataSet.getDataSet(RE4_STA_TUTO)
        # 5 TS with no. tilt-images:
        #   - TS_01 = 40
        #   - TS_03 = 40
        #   - TS_43 = 41
        #   - TS_45 = 41
        #   - TS_54 = 41
        #
        # 5 tomograms with a thickness of (px):
        #   - TS_01 = 340
        #   - TS_03 = 280
        #   - TS_43 = 300
        #   - TS_45 = 300
        #   - TS_54 = 280

    @classmethod
    def _runImportTs(cls, exclusionWords=None):
        print(magentaStr("\n==> Importing the tilt series:"))
        protTsImport = cls.newProtocol(ProtImportTs,
                                       filesPath=cls.ds.getFile(DataSetRe4STATuto.tsPath.value),
                                       filesPattern=DataSetRe4STATuto.tsPattern.value,
                                       exclusionWords=exclusionWords,
                                       anglesFrom=2,  # From tlt file
                                       voltage=DataSetRe4STATuto.voltage.value,
                                       magnification=DataSetRe4STATuto.magnification.value,
                                       sphericalAberration=DataSetRe4STATuto.sphericalAb.value,
                                       amplitudeContrast=DataSetRe4STATuto.amplitudeContrast.value,
                                       samplingRate=DataSetRe4STATuto.unbinnedPixSize.value,
                                       doseInitial=DataSetRe4STATuto.initialDose.value,
                                       dosePerFrame=DataSetRe4STATuto.dosePerTiltImgWithTltFile.value,
                                       tiltAxisAngle=DataSetRe4STATuto.tiltAxisAngle.value)

        cls.launchProtocol(protTsImport)
        tsImported = getattr(protTsImport, protTsImport.OUTPUT_NAME, None)
        return tsImported

    @classmethod
    def _runImportTomograms(cls, filesPattern=None):
        print(magentaStr("\n==> Importing the tomograms:"))
        protImportTomos = cls.newProtocol(ProtImportTomograms,
                                          filesPath=cls.ds.getFile(DataSetRe4STATuto.tsPath.value),
                                          filesPattern=filesPattern,
                                          samplingRate=DataSetRe4STATuto.sRateBin4.value)  # Bin 4
        cls.launchProtocol(protImportTomos)
        outTomos = getattr(protImportTomos, OUTPUT_NAME, None)
        return outTomos

    @classmethod
    def _runBinTs(cls, inTsSet):
        print(magentaStr("\n==> Binning the tilt-series with IMOD:"))
        protTSNormalization = cls.newProtocol(ProtImodTsNormalization,
                                              inputSetOfTiltSeries=inTsSet,
                                              binning=cls.bin4)
        cls.launchProtocol(protTSNormalization)
        outTsSet = getattr(protTSNormalization, OUTPUT_TILTSERIES_NAME, None)
        return outTsSet

    @classmethod
    def _runImportTrMatrix(cls, inTsSet):
        print(magentaStr("\n==> Importing the TS' transformation matrices with IMOD:"))
        protImportTrMatrix = cls.newProtocol(ProtImodImportTransformationMatrix,
                                             filesPath=cls.ds.getFile(DataSetRe4STATuto.tsPath.value),
                                             filesPattern=DataSetRe4STATuto.transformPattern.value,
                                             inputSetOfTiltSeries=inTsSet)
        cls.launchProtocol(protImportTrMatrix)
        outTsSet = getattr(protImportTrMatrix, OUTPUT_TILTSERIES_NAME, None)
        return outTsSet

    @staticmethod
    def _getHetTsSetTestData():
        expectedDimensions = {
            TS_01: tsDims40,
            TS_03: tsDims40,
            TS_43: tsDims41,
            TS_45: tsDims41,
            TS_54: tsDims41,
        }
        testAcqObjDict = {
            TS_01: DataSetRe4STATuto.testAcq01.value,
            TS_03: DataSetRe4STATuto.testAcq03.value,
            TS_43: DataSetRe4STATuto.testAcq43.value,
            TS_45: DataSetRe4STATuto.testAcq45.value,
            TS_54: DataSetRe4STATuto.testAcq54.value,
        }
        anglesCountDict = {
            TS_01: 40,
            TS_03: 40,
            TS_43: 41,
            TS_45: 41,
            TS_54: 41,
        }
        return expectedDimensions, testAcqObjDict, anglesCountDict

    def test_join_ts_homogeneous_sets(self):
        print(magentaStr("\n==> Join sets of TS with the same number of tilt-images:"))
        tsSet41imgs1 = self._runImportTs(exclusionWords='output 01 03 43 45')
        tsSet41imgs2 = self._runImportTs(exclusionWords='output 01 03 54')
        protUnion = self.newProtocol(ProtUnionSet)
        protUnion.inputSets.append(tsSet41imgs1)
        protUnion.inputSets.append(tsSet41imgs2)
        protUnion.setObjLabel('join homogen tsSets')
        self.launchProtocol(protUnion)
        # Check the tests
        testAcqObjDict = {
            TS_43: DataSetRe4STATuto.testAcq43.value,
            TS_45: DataSetRe4STATuto.testAcq45.value,
            TS_54: DataSetRe4STATuto.testAcq54.value,
        }
        self.checkTiltSeries(getattr(protUnion, 'outputSet', None),
                             expectedSetSize=len(testAcqObjDict),
                             expectedSRate=DataSetRe4STATuto.unbinnedPixSize.value,
                             expectedDimensions=tsDims41,
                             testSetAcqObj=testAcqObjDict[TS_54],
                             testAcqObj=testAcqObjDict,
                             anglesCount=41,
                             imported=True,
                             isHetereogeneousSet=False)

    def test_join_ts_heterogeneous_sets(self):
        print(magentaStr("\n==> Join sets of TS with different number of tilt-images:"))
        tsSet41imgs = self._runImportTs(exclusionWords='output 01 03')
        tsSet40imgs = self._runImportTs(exclusionWords='output 43 45 54')
        protUnion = self.newProtocol(ProtUnionSet)
        protUnion.inputSets.append(tsSet41imgs)
        protUnion.inputSets.append(tsSet40imgs)
        protUnion.setObjLabel('join het tsSets')
        self.launchProtocol(protUnion)
        # Check the results
        expectedDimensions, testAcqObjDict, anglesCountDict = self._getHetTsSetTestData()
        self.checkTiltSeries(getattr(protUnion, 'outputSet', None),
                             expectedSetSize=len(testAcqObjDict),
                             expectedSRate=DataSetRe4STATuto.unbinnedPixSize.value,
                             expectedDimensions=expectedDimensions,
                             testAcqObj=testAcqObjDict,
                             anglesCount=anglesCountDict,
                             imported=True,
                             isHetereogeneousSet=True)

    def test_join_ts_heterogeneous_sets_with_ali(self):
        print(magentaStr("\n==> Join sets of TS (+ali) with different number of tilt-images:"))
        tsSet41imgs = self._runImportTs(exclusionWords='output 01 03')
        tsSet40imgs = self._runImportTs(exclusionWords='output 43 45 54')
        tsSet41imgsWithAli = self._runImportTrMatrix(tsSet41imgs)
        tsSet40imgsWithAli = self._runImportTrMatrix(tsSet40imgs)
        protUnion = self.newProtocol(ProtUnionSet)
        protUnion.inputSets.append(tsSet41imgsWithAli)
        protUnion.inputSets.append(tsSet40imgsWithAli)
        protUnion.setObjLabel('join het tsSets')
        self.launchProtocol(protUnion)
        # Check the results
        expectedDimensions, testAcqObjDict, anglesCountDict = self._getHetTsSetTestData()
        self.checkTiltSeries(getattr(protUnion, 'outputSet', None),
                             expectedSetSize=len(testAcqObjDict),
                             expectedSRate=DataSetRe4STATuto.unbinnedPixSize.value,
                             expectedDimensions=expectedDimensions,
                             testAcqObj=testAcqObjDict,
                             anglesCount=anglesCountDict,
                             isHetereogeneousSet=True,
                             hasAlignment=True,
                             alignment=ALIGN_2D)

    def test_join_tomos_heterogeneous_sets(self):
        print(magentaStr("\n==> Join sets of tomograms with different thickness:"))
        tomoSetThk300 = self._runImportTomograms(filesPattern='TS_4*.mrc')
        tomoSetThk340 = self._runImportTomograms(filesPattern='TS_01.mrc')
        tomoSetThk280_1 = self._runImportTomograms(filesPattern='TS_03.mrc')
        tomoSetThk280_2 = self._runImportTomograms(filesPattern='TS_54.mrc')
        protUnion = self.newProtocol(ProtUnionSet)
        protUnion.inputSets.append(tomoSetThk300)
        protUnion.inputSets.append(tomoSetThk340)
        protUnion.inputSets.append(tomoSetThk280_1)
        protUnion.inputSets.append(tomoSetThk280_2)
        protUnion.setObjLabel('join het tomoSets')
        self.launchProtocol(protUnion)
        # Check the results
        expectedDimensionsDict = {
            TS_01: tomoDimsThk340,
            TS_03: tomoDimsThk280,
            TS_43: tomoDimsThk300,
            TS_45: tomoDimsThk300,
            TS_54: tomoDimsThk280,
        }
        self.checkTomograms(getattr(protUnion, 'outputSet', None),
                            expectedSetSize=len(expectedDimensionsDict),
                            expectedSRate=self.bin4SRate,
                            expectedDimensions=expectedDimensionsDict,
                            isHetereogeneousSet=True)

    def test_join_tomos_homogeneous_sets(self):
        print(magentaStr("\n==> Join sets of tomograms with different thickness:"))
        tomoSetThk300_1 = self._runImportTomograms(filesPattern='TS_43.mrc')
        tomoSetThk300_2 = self._runImportTomograms(filesPattern='TS_45.mrc')
        protUnion = self.newProtocol(ProtUnionSet)
        protUnion.inputSets.append(tomoSetThk300_1)
        protUnion.inputSets.append(tomoSetThk300_2)
        protUnion.setObjLabel('join homogen tomoSets')
        self.launchProtocol(protUnion)
        # Check the results
        self.checkTomograms(getattr(protUnion, 'outputSet', None),
                            expectedSetSize=2,
                            expectedSRate=self.bin4SRate,
                            expectedDimensions=tomoDimsThk300,
                            isHetereogeneousSet=False)



