# **************************************************************************
# *
# * Authors:     Alberto García Mena (alberto.garcia@cnb.csic.es)
# *
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

import time
import os
from glob import glob
from pwem.protocols.protocol_import.base import ProtImport
import pyworkflow as pw
from pyworkflow.protocol import params, STEPS_PARALLEL
import pyworkflow.protocol.constants as cons
from tomo.convert.mdoc import MDoc
import pwem.objects as emobj
import tomo.objects as tomoObj
from tomo.objects import SetOfTiltSeries
from pwem.objects.data import Transform
from pyworkflow.object import Integer
from tomo.protocols import ProtTomoBase
from pwem.emlib.image import ImageHandler

OUT_STS = "SetOfTiltSeries"


class ProtComposeTS(ProtImport, ProtTomoBase):
    """ Compose in streaming a set of tilt series based on a sets of micrographs and mdoc files.
    Two time parameters are abailable for the streaming behaviour:
    Time for next tilt and Time for next Tilt Serie
    """
    _devStatus = pw.BETA
    _label = 'Compose Tilt Serie'
    _possibleOutputs = {OUT_STS: SetOfTiltSeries}

    def __init__(self, **args):
        ProtImport.__init__(self, **args)
        self.stepsExecutionMode = STEPS_PARALLEL  # Defining that the protocol contain parallel steps
        self.newSteps = []
        self.listMdocsRead = []
        self.list_reading = []
        self.TiltSeries = None
        self.waitingMdoc = True
        self.time4NextMic = 10
        self.time4NextTS_current = time.time()

    # -------------------------- DEFINES AND STEPS -----------------------
    def _defineParams(self, form):
        form.addSection(label='Import')

        form.addParam('inputMicrographs', params.PointerParam, allowNull=False,
                      pointerClass='SetOfMicrographs',
                      important=True,
                      label="Input micrographs",
                      help='Select the SetOfMicrographs to import')

        form.addParam('filesPath', params.PathParam,
                      label="Path with the *.mdoc files for each TiltSerie",
                      help="Root directory of the tilt-series. "
                           "Will be search the *.mdoc file for each Tilt Serie")

        form.addParam('mdoc_bug_Correction', params.BooleanParam, default=False,
                      label="mdoc bug Correction",
                      help="Setting True, the mdoc generated by SerialEM "
                           "will be read considering the bug")

        form.addSection('Streaming')

        form.addParam('dataStreaming', params.BooleanParam, default=True,
                      label="Process data in streaming?",
                      help="Select this option if you want import data as it "
                           "is generated and process on the fly by next "
                           "protocols. In this case the protocol will "
                           "keep running to check new files and will "
                           "update the output Set, which can "
                           "be used right away by next steps.")

        form.addParam('time4NextTilt', params.IntParam, default=180,
                      condition='dataStreaming',
                      label="Time for next Tilt (secs)",
                      help="Delay (in seconds) until the next tilt is "
                           "registered in the mdoc file. After "
                           "timeout, if there is no new tilt, the tilt serie "
                           "is considered as completed."
                           "Minimum time recomended 20 segs")
        form.addParam('time4NextTS', params.IntParam, default=1800,
                      condition='dataStreaming',
                      label="Time for next TiltSerie (secs)",
                      help="Interval of time (in seconds) after which, "
                           "if no new tilt serie is detected, the protocol will "
                           "end. "
                           "The default value is  high (30 min) to "
                           "avoid the protocol finishes during the acq of the "
                           "microscope. You can also stop it from right click "
                           "and press STOP_STREAMING.\n")
        form.addParallelSection(threads=3, mpi=1)

    def _initialize(self):

        self.time4NextTS_current = time.time()
        self.ih = ImageHandler()

    def _insertAllSteps(self):
        self._insertFunctionStep(self._initialize)
        self.CloseStep_ID = self._insertFunctionStep('closeSet',
                                                     prerequisites=[],
                                                     wait=True)
        self.newSteps.append(self.CloseStep_ID)

    def _stepsCheck(self):
        """
        Read all the mdoc files abailable, sort by date and run 'readMdoc'

        """
        current_time = time.time()
        delay = int(current_time - self.time4NextTS_current)
        if self.waitingMdoc:
            self.debug('Timeout for next TiltSerie (.mdoc file) ' +
                       str(self.time4NextTS.get()) + ' segs ...')
        self.waitingMdoc = False
        self.list_current = self.findMdoc()
        self.list_remain = [x for x in self.list_current if x not in self.listMdocsRead
                       and x not in self.list_reading]

        # STREAMING CHECKPOINT
        if delay > int(self.time4NextTS.get()):
            self.info('Time waiting next Tilt Serie has expired. ({}s)'.format(
                str(self.time4NextTS.get())))
            output_step = self._getFirstJoinStep()
            if output_step and output_step.isWaiting():
                output_step.setStatus(cons.STATUS_NEW)

        elif self.list_remain == [] and self._loadInputList()[1] == False:
            self.info('There is no more mdoc file to read and the set of micrographs is closed')
            output_step = self._getFirstJoinStep()
            if output_step and output_step.isWaiting():
                output_step.setStatus(cons.STATUS_NEW)

        elif self.list_remain:
            self.waitingMdoc = True
            #self.listMdocsRead.append(list_remain[0])
            self.time4NextTS_current = time.time()
            self.list_reading.append(self.list_remain[0])
            new_step_id = self._insertFunctionStep('readMdoc', self.list_remain[0],
                                                   prerequisites=[], wait=False)
            self.newSteps.append(new_step_id)
            self.updateSteps()



    def closeSet(self):
        pass

    def _getFirstJoinStep(self):
        for s in self._steps:
            if s.funcName == self._getFirstJoinStepName():
                return s
        return None

    def _getFirstJoinStepName(self):
        # This function will be used for streaming, to check which is
        # the first function that need to wait for all micrographs
        # to have completed, this can be overwritten in subclasses
        # (eg in Xmipp 'sortPSDStep')
        return 'closeSet'

    # -------------------------- MAIN FUNCTIONS -----------------------
    def findMdoc(self):
        """
        :return: return a sorted by date list of all mdoc files in the path
        """
        """ return a sorted by date list of all mdoc files in the path """
        fpath = self.filesPath.get()
        self.MDOC_DATA_SOURCE = glob(os.path.join(fpath, '*.mdoc'))
        self.MDOC_DATA_SOURCE.sort(key=os.path.getmtime)
        return self.MDOC_DATA_SOURCE

    def readMdoc(self, file2read):
        """
        Main function to launch the match with the set of micrographs and
        launch the create of SetOfTiltSeries and each TiltSerie
        :param file2read: mdoc file in the path
        """
        self.info('Reading mdoc file: {}'.format(file2read))
        statusMdoc, mdoc_order_angle_list = self.readingMdocTiltInfo(file2read)
        # STREAMING CHECKPOINT
        while time.time() - self.readDateFile(file2read) < \
                self.time4NextTilt.get():
            self.debug('Waiting next tilt... ({} tilts found)'.format(
                len(mdoc_order_angle_list)))
            time.sleep(self.time4NextTilt.get() / 2)
            statusMdoc, mdoc_order_angle_list = \
                self.readingMdocTiltInfo(file2read)
        self.info('mdoc file {} is considered closed'.format(os.path.basename(file2read)))
        if statusMdoc:
            if len(mdoc_order_angle_list) < 3:
                self.info('Mdoc error. Less than 3 tilts in the serie')
                self.listMdocsRead.append(file2read)

            elif self.matchTS(mdoc_order_angle_list, file2read):
                self.createTS(self.mdoc_obj)
                self.listMdocsRead.append(file2read)
                self.listMdocsRead.append(file2read)

                self.info("Tilt Serie ({} tilts) composed from mdoc file: {}\n".
                    format(len(mdoc_order_angle_list), file2read))
                # SUMMARY INFO
                summaryF = self._getPath("summary.txt")
                summaryF = open(summaryF, "a")
                summaryF.write(
                    "Tilt Serie ({} tilts) composed from mdoc file: {}\n".
                    format(len(mdoc_order_angle_list), file2read))
                summaryF.close()


        self.list_reading.remove(file2read)

    def readingMdocTiltInfo(self, file2read):
        """
        :param file2read: mdoc file to read
        :return: Bool: if the validation of the mdoc goes good or bad
                 mdoc_order_angle_list: list with info for each tilt
                    file, acquisition order and tilt Angle
        """
        mdoc_order_angle_list = []
        self.mdoc_obj = MDoc(file2read)
        validation_error = self.mdoc_obj.read(ignoreFilesValidation=True)
        if validation_error:
            self.debug(validation_error)
            return False, mdoc_order_angle_list
        for tilt_metadata in self.mdoc_obj.getTiltsMetadata():
            filepath = tilt_metadata.getAngleMovieFile()
            tiltA = tilt_metadata.getTiltAngle()
            if self.mdoc_bug_Correction.get():
                filepath, tiltA = self.fixingMdocBug(filepath, tiltA)

            mdoc_order_angle_list.append((filepath,
                '{:03d}'.format(tilt_metadata.getAcqOrder()), tiltA))
        return True, mdoc_order_angle_list


    def fixingMdocBug(self, filepath, tiltA):
        idx = filepath.find(']_')
        filepath = filepath[:idx + 2] + filepath[idx + 2].upper() + filepath[idx + 3:]
        if float(tiltA) - round(float(tiltA), 0) != 0:
            filepath = filepath.replace(str(tiltA), str(round(float(tiltA))) + '.00')
            tiltA = str(round(float(tiltA))) + '.00'
        return filepath, tiltA

    def readDateFile(self, file):
        return os.path.getmtime(file)

    def matchTS(self, mdoc_order_angle_list, file2read):
        """
        Edit the self.listOfMics with the ones in the mdoc file
        :param mdoc_order_angle_list: for each tilt:
                filename, acquisitionOrder, Angle
        """
        len_mics_input_1, streamOpen = self._loadInputList()
        # STREAMING CHECKPOINT
        while len(mdoc_order_angle_list) > len_mics_input_1 and streamOpen == True:
            self.info('Tilts in the mdoc {}: {} Micrographs abailables: {}'.format(
                os.path.basename(file2read), len(mdoc_order_angle_list), len(self.listOfMics)))
            self.info('Waiting next micrograph...')
            time.sleep(self.time4NextMic)
            len_mics_input_1, streamOpen = self._loadInputList()

        self.info('Tilts in the mdoc file: {}\n'
                  'Micrographs availables: {}'.format(
            len(mdoc_order_angle_list), len(self.listOfMics)))

        #MATCH
        list_mdoc_files = [os.path.splitext(os.path.basename(fp[0]))[0] for fp in mdoc_order_angle_list] #quitar la extension que no tiene por k ser mrc!!
        list_mics_matched = []
        for x, mic in enumerate(self.listOfMics):
            if os.path.splitext(mic.getMicName())[0] in list_mdoc_files:
                list_mics_matched.append(mic)

        if len(list_mics_matched) != len(mdoc_order_angle_list):
            if streamOpen == False:
                self.info('Micrographs doesnt match with mdoc {} read'
                      'Number of mics: {}, number of mics on mdoc: {}\n'
                       'The set of micrographs is closed but has not all'
                       ' the micrographs the mdoc refer'.format(file2read,
                len(self.listOfMics), len(mdoc_order_angle_list)))
                self.listMdocsRead.append(file2read)
                return False
            else:
                self.info('The micrographs read does not belong the mdoc {}. '
                          'The mdoc will be read in furute'.format(os.path.basename(file2read)))
        else:
            self.info('Micrographs matched for the mdoc file: {}'.format(
                len(list_mics_matched)))
            return True

    def _loadInputList(self):
        """ Load the input set of mics and create a list. """
        mic_file = self.inputMicrographs.get().getFileName()
        self.debug("Loading input db: %s" % mic_file)
        mic_set = emobj.SetOfMicrographs(filename=mic_file)
        mic_set.loadAllProperties()
        self.listOfMics = [m.clone() for m in mic_set]
        mic_set.close()
        return len(self.listOfMics), mic_set.isStreamOpen()

    def createTS(self, mdoc_obj):
        """
        Create the SetOfTiltSeries and each TiltSerie
        :param mdoc_obj: mdoc object to manage
        """
        self.info('Tilt Serie {} beeing composed...'.format(mdoc_obj.getTsId()))
        if self.TiltSeries is None:
            SOTS = self._createSetOfTiltSeries(suffix='')
            SOTS.setStreamState(SOTS.STREAM_OPEN)
            SOTS.enableAppend()
            self._defineOutputs(TiltSeries=SOTS)
            self._defineSourceRelation(self.inputMicrographs, SOTS)
            self._store(SOTS)
        else:
            SOTS = self.TiltSeries
            SOTS.setStreamState(SOTS.STREAM_OPEN)
            SOTS.enableAppend()
            self._store(SOTS)

        file_order_angle_list = []
        accumulated_dose_list = []
        incoming_dose_list = []
        for tilt_metadata in mdoc_obj.getTiltsMetadata():
            filepath = tilt_metadata.getAngleMovieFile()
            tiltAngle = tilt_metadata.getTiltAngle()
            if self.mdoc_bug_Correction.get():
                filepath, tiltAngle = self.fixingMdocBug(filepath, tiltAngle)

            file_order_angle_list.append((filepath,  # Filename
                                          '{:03d}'.format(tilt_metadata.getAcqOrder()),  # Acquisition
                                          tiltAngle))
            accumulated_dose_list.append(tilt_metadata.getAccumDose())
            incoming_dose_list.append(tilt_metadata.getIncomingDose())

        file_ordered_angle_list = sorted(file_order_angle_list,
                                         key=lambda angle: float(angle[2]))
        # Tilt Serie object
        ts_obj = tomoObj.TiltSeries()
        len_ac = Integer(len(file_ordered_angle_list))
        ts_obj.setAnglesCount(len_ac)
        ts_obj.setTsId(mdoc_obj.getTsId())
        acq = ts_obj.getAcquisition()
        acq.setVoltage(mdoc_obj.getVoltage())
        acq.setMagnification(mdoc_obj.getMagnification())
        acq.setSphericalAberration(self.listOfMics[0].getAcquisition().getSphericalAberration())
        acq.setAmplitudeContrast(self.listOfMics[0].getAcquisition().getAmplitudeContrast())
        ts_obj.getAcquisition().setTiltAxisAngle(mdoc_obj.getTiltAxisAngle())
        origin = Transform()
        ts_obj.setOrigin(origin)
        SOTS.append(ts_obj)

        self.setingTS(SOTS, ts_obj, file_ordered_angle_list,
                      incoming_dose_list, accumulated_dose_list)

        SOTS.setStreamState(SOTS.STREAM_CLOSED)
        ts_obj.write(properties=False)
        SOTS.update(ts_obj)
        SOTS.updateDim()
        SOTS.write()
        self._store(SOTS)


    def setingTS(self, SOTS, ts_obj, file_ordered_angle_list,
                 incoming_dose_list, accumulated_dose_list):
        """
        Set all the info in each tilt and set the ts_obj information with all
        the tilts
        :param SOTS: Set Ot Tilt Serie
        :param ts_obj: Tilt Serie Object to add tilts
        :param file_ordered_angle_list: list of files sorted by angle
        :param incoming_dose_list: list of dose
        :param accumulated_dose_list: list of accumulated dose
        :param origin: transform matrix
        :return:
        """
        ts_fn = self._getOutputTiltSeriesPath(ts_obj)
        ts_fn_dw = self._getOutputTiltSeriesPath(ts_obj, '_DW')
        counter_ti = 0

        TSAngleFile = self._getPath("{}.rawtlt".format(ts_obj.getTsId()))
        TSAngleFile = open(TSAngleFile, "a")
        for n in file_ordered_angle_list:
            TSAngleFile.write('{}\n'.format(str(n[2])))
        TSAngleFile.close()

        for f, to, ta in file_ordered_angle_list:
            try:
                for mic in self.listOfMics:
                    if ts_obj.getSamplingRate() is None:
                        ts_obj.setSamplingRate(mic.getSamplingRate())
                    if SOTS.getSamplingRate() is None:
                        SOTS.setSamplingRate(mic.getSamplingRate())
                    if os.path.basename(f) in mic.getMicName():
                        ti = tomoObj.TiltImage()
                        ti.setLocation(mic.getFileName())
                        ti.setTsId(ts_obj.getObjId())
                        ti.setObjId(counter_ti + 1)
                        ti.setIndex(counter_ti + 1)
                        ti.setAcquisitionOrder(int(to))
                        ti.setTiltAngle(ta)
                        ti.setSamplingRate(mic.getSamplingRate())
                        ti.setAcquisition(ts_obj.getAcquisition().clone())
                        ti.getAcquisition().setDosePerFrame(
                            incoming_dose_list[int(to) - 1])
                        ti.getAcquisition().setAccumDose(
                            accumulated_dose_list[int(to) - 1])
                        ti_fn, ti_fn_dw = self._getOutputTiltImagePaths(ti)
                        new_location = (counter_ti + 1, ts_fn)

                        self.ih.convert(mic.getFileName(), new_location)
                        ti.setLocation(new_location)
                        if os.path.exists(ti_fn_dw):
                            self.ih.convert(ti_fn_dw, (counter_ti, ts_fn_dw))
                            pw.utils.cleanPath(ti_fn_dw)
                        ts_obj.append(ti)
                        counter_ti += 1
            except Exception as e:
                self.error(e)

    # -------------------------- AUXILIAR FUNCTIONS -----------------------
    def _getOutputTiltSeriesPath(self, ts, suffix=''):
        return self._getExtraPath('%s%s.mrcs' % (ts.getTsId(), suffix))

    def _getOutputTiltImagePaths(self, tilt_image):
        """ Return expected output path for correct movie and DW one.
        """
        base = self._getExtraPath(self._getTiltImageMRoot(tilt_image))
        return base + '.mrc', base + '_Out.mrc'

    def _getTiltImageMRoot(self, tim):
        return '%s_%02d' % (tim.getTsId(), tim.getObjId())

    def _validate(self):
        pass


    def _summary(self):
        summary = []

        summaryF = self._getPath("summary.txt")
        if not os.path.exists(summaryF):
            summary.append("No summary file yet.")
        else:
            summaryF = open(summaryF, "r")
            for line in summaryF.readlines():
                summary.append(line.rstrip())
            summaryF.close()

        return summary
