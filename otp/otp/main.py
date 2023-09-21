import csv
from genericpath import isfile
from imghdr import tests
from re import S
from signal import signal
from numpy import sign
import pandas as pd
import nidcpower
import hightime
# from driver.P8XL import P8XL
import contextlib
import os 

target_x = 13970
target_y = 6065.5

current_x = 1650
current_y = 21865.5
p8_address = 'GPIB0::9::INSTR'
# s
aperture_time = 40e-3
stress = 4.6
csv_name = "A_otpAA.csv"
class SRAM16x16:

    # class sequence():


    def __init__(self, dir_fVec, fMap):
        # self.df = pd.read_csv(fVec)
        pinMap = {}
        self.all0 = 'RDATA1'
        self.all1 = 'WDATA2'
        self.chkbrd1 = 'RDATA3'
        self.chkbrd0 = 'checkboard0'
        self.dictVec = {}
        self.dictVec_df = {}
        for filename in os.listdir(dir_fVec):
            f = os.path.join(dir_fVec, filename)
            if os.path.isfile(f):
                if self.all0 in f:
                    self.dictVec[self.all0] = f
                    self.dictVec_df[self.all0] = pd.read_csv(f)
                elif self.all1 in f:
                    self.dictVec[self.all1] = f
                    self.dictVec_df[self.all1] = pd.read_csv(f)
                elif self.chkbrd0 in f:
                    self.dictVec[self.chkbrd0] = f
                    self.dictVec_df[self.chkbrd0] = pd.read_csv(f)
                elif self.chkbrd1 in f:
                    self.dictVec[self.chkbrd1] = f
                    self.dictVec_df[self.chkbrd1] = pd.read_csv(f)
        
        with open(fMap) as fin:
            for row in csv.DictReader(fin, skipinitialspace=True):
                pinMap[row['name']] = row['chn']
        self.pinMap = pinMap
        self.VDD = 1.5

    def commonSetting(self, sess : nidcpower.Session):
        sess.source_mode = nidcpower.SourceMode.SEQUENCE
        sess.power_line_frequency = 50
        sess.aperture_time_units = nidcpower.ApertureTimeUnits.SECONDS
        sess.samples_to_average = 1
        sess.measure_when = nidcpower.MeasureWhen.AUTOMATICALLY_AFTER_SOURCE_COMPLETE
        sess.measure_record_length_is_finite = True
        sess.voltage_level_autorange = True
        sess.output_connected = False

        df = self.dictVec_df[self.all0]
        pinMap = self.pinMap

        chnNameCK = pinMap['CK']
        chnCK = sess.channels[f'{chnNameCK}']
        chnCK.source_delay = 1e-3
        chnCK.aperture_time = aperture_time
        # chnCK.measure_complete_event_delay = 10e-3

        for sigName in df.columns:
            if sigName=='#' or sigName=='CK': continue

            chnName = pinMap[sigName]
            chn = sess.channels[f'{chnName}']
            chn.measure_when = nidcpower.MeasureWhen.ON_MEASURE_TRIGGER
            chn.measure_trigger_type = nidcpower.TriggerType.DIGITAL_EDGE
            chn.digital_edge_measure_trigger_input_terminal = f'/SMU4163/Engine{chnNameCK}/SourceCompleteEvent'
            chn.aperture_time = aperture_time
            chn.source_delay = 5e-5
            chn.source_trigger_type  = nidcpower.TriggerType.DIGITAL_EDGE
            chn.digital_edge_source_trigger_input_terminal  = f'/SMU4163/Engine{chnNameCK}/SourceTrigger'

    def populate(self, sess : nidcpower.Session):
        # df = self.df
        pinMap = self.pinMap
        for sequenceName in [self.all0, self.all1, self.chkbrd1]:
            fVec = self.dictVec[sequenceName]
            df = pd.read_csv(fVec)

            properties_used = ['output_enabled', 'output_function', 'voltage_level']
            sess.create_advanced_sequence(sequence_name=sequenceName, property_names=properties_used, set_as_active_sequence=True)

            numCycle = len(df['WE'])
            print(numCycle*1)
            for iCyc in range(numCycle):
                for iPhase in range(1):
                    sess.create_advanced_sequence_step(set_as_active_step=True)
                    for sigName in df.columns:
                        if sigName=='#': continue
                        print(sequenceName)
                        chnName = pinMap[sigName]
                        val = df[sigName][iCyc]
                        # if sigName=='CK':
                        #     val = 1 if iPhase==1 else 0
                        # #print(iCyc,sigName,val)
                        # if sigName=='VBNL_N':
                        #     val = 4 if iPhase==1 else 0
                        # if sigName=='VDD33_N':
                        #     val = 4 if iPhase==1 else 0
                        # if sigName=='VDD':
                        #     val = 1.1
                        chn = sess.channels[f'{chnName}']
                        if val=='Z':
                            chn.output_enabled = False
                            chn.output_connected = False
                        elif val==1 or val==0 or val=='1' or val=='0':
                            val = int(val)
                            chn.output_enabled = True
                            chn.output_connected = True
                            chn.output_function = nidcpower.OutputFunction.DC_VOLTAGE
                            chn.voltage_level = self.VDD * val
                        elif val==1 or val==0 or val=='1' or val=='0':
                            val = int(val)
                            chn.output_enabled = True
                            chn.output_connected = True
                            chn.output_function = nidcpower.OutputFunction.DC_VOLTAGE
                            chn.voltage_level = self.VDD * val
                        elif val==4 or val==4.0 or val=='4' or val=='4.0':
                            val = int(val)
                            chn.output_enabled = True
                            chn.output_connected = True
                            chn.output_function = nidcpower.OutputFunction.DC_VOLTAGE
                            chn.voltage_level = stress
                        elif val==1.1 or val=='1.1':
                            val = float(val)
                            chn.output_enabled = True
                            chn.output_connected = True
                            chn.output_function = nidcpower.OutputFunction.DC_VOLTAGE
                            chn.voltage_level = val
                        else:
                            raise ValueError(val)
                        chn.aperture_time = aperture_time
                        chn.current_limit_range = 1e-3
                        chn.current_limit       = 1e-3

    def writeResult(self, sess, fout, sequenceName):
        df = self.dictVec_df[sequenceName]
        pinMap = self.pinMap
        timeout = hightime.timedelta(seconds=(1000))

        hdrs = []
        cols = []
        print(time.time())
        for sigName in df.columns:
            if sigName=='#': continue
            chnName = pinMap[sigName]
            chn = sess.channels[chnName]
            num  = chn.fetch_backlog
            print(f'num of fetch_backlog={num}')
            meas = chn.fetch_multiple(num, timeout=timeout)
            #print(chnName, num, meas)
            hdrs.append(sigName+"_Voltage")
            hdrs.append(sigName+"_Current")
            cols.append(meas)
        print(time.time())

        writer = csv.writer(fout)
        writer.writerow(hdrs)
        for i in range(len(cols[0])):
            rowV = [c[i].voltage for c in cols]
            rowI = [c[i].current for c in cols]
            row = list(zip(rowV, rowI))
            row = [word for meas in row for word in meas]
            # print(row)
            writer.writerow(row)

    def testSRAM(self, session: nidcpower.Session, x, y, foutDIR):
        for sequenceName in [self.all0, self.all1, self.chkbrd1]:
            session.active_advanced_sequence = sequenceName
            session.active_advanced_sequence_step = 0
            session.commit()

            with contextlib.ExitStack() as ctxt:

                for sigName in self.dictVec_df[sequenceName].columns:
                    if sigName=='#' or sigName=='CK': continue

                    chnName = self.pinMap[sigName]
                    chn = session.channels[f'{chnName}']
                    ctxt.enter_context(chn.initiate())
                
                chnNameCK = self.pinMap['CK']
                chnCK = session.channels[f'{chnNameCK}']
                ctxt.enter_context(chnCK.initiate())

                chnCK.wait_for_event(nidcpower.Event.SEQUENCE_ENGINE_DONE, timeout=timeout)
                # date = f"{str(time.localtime().tm_mon)}_{str(time.localtime().tm_mday)}_{str(time.localtime().tm_hour())}_{str(time.localtime().tm_min)}"
                with open(f'{foutDIR}OTPAA___{x}_{y}_{sequenceName}_{csv_name}_stress_{stress}_apertureTime{aperture_time}__UB.csv', 'w', newline='') as fout:
                    self.writeResult(session, fout, sequenceName)

if __name__=='__main__':
    import argparse
    import time

    parser = argparse.ArgumentParser()


    parser.add_argument('--lot', type=str, default='C1.001',
                        help='Lot id')
    parser.add_argument('--wafer', type=str, default='1',
                        help='Wafer id in the lot.')
    parser.add_argument('--die', type=str, action='append',
                        help='Die row/column index on the wafer, e.g. [0,0] refers ' +
                             'to the die at the center of the wafer. '
                             'If not given, the center die will be tested.')
    args = parser.parse_args()
    if isinstance(args.die, list) and len(args.die) > 0:
        dies = args.die
    else:
        dies = [('0,0')]

    continueTest = True
    tCount = 0
    out_dir = 'idk/'
    pinMap_dir = os.getcwd()
    vec_dir = os.getcwd()
    map_file = ''
    for filename in os.listdir(pinMap_dir):
        f = os.path.join(pinMap_dir, filename)
        if "map" in f:
            map_file = f
            print(f)
    

    sram256bit = SRAM16x16(vec_dir, map_file)
    delay_in_seconds = 0.01
    timeout=hightime.timedelta(seconds=(delay_in_seconds*7000+30))
    # for mock-up runs
    options = {'simulate': False, 'driver_setup': {'Model': '4163', 'BoardType': 'PXIe', }, }
    # for real runs
    #options = {}


    with nidcpower.Session(resource_name='SMU4163', options=options) as session:
        sram256bit.commonSetting(session)
        sram256bit.populate(session)
        
        # for die in dies:

        #     if not continueTest: break
        #     die = die.translate({ord('['): None, ord(']'): None})  # strip '[' and ']'
        #     dieXCoord, dieYCoord = map(int, die.split(','))
        #     with p8xl.connect():
        #         p8xl.getWaferParams()
        #         p8xl.moveToDie(dieXCoord, dieYCoord)
        #     with p8xl.connect():
        #         p8xl.getWaferParams()
        #     # p8xl.driveDistanceX(int(target_x-current_x))
        #     # p8xl.driveDistanceY(int(target_y-current_y))
        #         time.sleep(1)
        #         # p8xl.upZ()
        # try:
        dieXCoord = "x"
        dieYCoord = "y"
        sram256bit.testSRAM(session, dieXCoord, dieYCoord, out_dir)

            # testSRAM16x16(
            #     fVec = f'{vec_dir}/vec_SRAM32x32_all0.csv',
            #     fMap = f'{pinMap_dir}',
            #     fOut = f'{out_dir}/out_all0_{str(dieXCoord)+"_"+str(dieYCoord)}.csv',
            #     )
            # testSRAM16x16(
            #     fVec=f'{vec_dir}/vec_SRAM32x32_all1.csv',
            #     fMap=f'{pinMap_dir}',
            #     fOut=f'{out_dir}/out_all1_{str(dieXCoord) + "_" + str(dieYCoord)}.csv',
            # )
            # testSRAM16x16(
            #     fVec=f'{vec_dir}/vec_SRAM32x32_checkerborder0.csv',
            #     fMap=f'{pinMap_dir}',
            #     fOut=f'{out_dir}/out_chkbrd0_{str(dieXCoord) + "_" + str(dieYCoord)}.csv',
            # )
            # testSRAM16x16(
            #     fVec=f'{vec_dir}/vec_SRAM32x32_checkerborder1.csv',
            #     fMap=f'{pinMap_dir}',
            #     fOut=f'{out_dir}/out_chkbrd1_{str(dieXCoord) + "_" + str(dieYCoord)}.csv',
            # )
        # finally:
        #     with p8xl.connect():
        #         p8xl.downZ()
        #         pass
        # tCount += 1
        # if tCount >= 20:
        #     tCount = 0
        #     p8xl.polish()
