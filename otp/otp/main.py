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
aperture_time = 1e-3
stress = 4.6
csv_name = "A_otpAA.csv"
class SRAM16x16:

    # class sequence():


    def __init__(self, dir_fVec, fMap):
        # self.df = pd.read_csv(fVec)
        pinMap = {}
        self.dacVec = 'vec565'

        self.dictVec = {}
        self.dictVec_df = {}
        for filename in os.listdir(dir_fVec):
            f = os.path.join(dir_fVec, filename)
            if os.path.isfile(f):
                if self.dacVec in f:
                    self.dictVec[self.dacVec] = f
                    self.dictVec_df[self.dacVec] = pd.read_csv(f)
                # elif self.all1 in f:
                #     self.dictVec[self.all1] = f
                #     self.dictVec_df[self.all1] = pd.read_csv(f)
                # elif self.chkbrd0 in f:
                #     self.dictVec[self.chkbrd0] = f
                #     self.dictVec_df[self.chkbrd0] = pd.read_csv(f)
                # elif self.chkbrd1 in f:
                #     self.dictVec[self.chkbrd1] = f
                #     self.dictVec_df[self.chkbrd1] = pd.read_csv(f)
        
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
        sess.autorange = True
        sess.measure_when = nidcpower.MeasureWhen.AUTOMATICALLY_AFTER_SOURCE_COMPLETE
        sess.measure_record_length_is_finite = True
        sess.voltage_level_autorange = True
        sess.output_connected = False

        df = self.dictVec_df[self.dacVec]
        pinMap = self.pinMap

        chnNameVCC = pinMap['vcc']
        chnCK = sess.channels[f'{chnNameVCC}']
        chnCK.source_delay = 1e-3
        chnCK.aperture_time = aperture_time
        chnCK.measure_complete_event_delay = 10e-3

        for sigName in df.columns:
            if sigName=='#' or sigName=='vcc': continue

            chnName = pinMap[sigName]
            chn = sess.channels[f'{chnName}']
            chn.measure_when = nidcpower.MeasureWhen.ON_MEASURE_TRIGGER
            chn.measure_trigger_type = nidcpower.TriggerType.DIGITAL_EDGE
            chn.digital_edge_measure_trigger_input_terminal = f'/SMU4163/Engine{chnNameVCC}/SourceCompleteEvent'
            chn.aperture_time = aperture_time
            chn.source_delay = 5e-5
            chn.source_trigger_type  = nidcpower.TriggerType.DIGITAL_EDGE
            chn.digital_edge_source_trigger_input_terminal  = f'/SMU4163/Engine{chnNameVCC}/SourceTrigger'

    def populate(self, sess : nidcpower.Session):
        # df = self.df
        pinMap = self.pinMap
        for sequenceName in [self.dacVec]:
            fVec = self.dictVec[sequenceName]
            df = pd.read_csv(fVec)

            properties_used = ['output_enabled', 'output_function', 'voltage_level', 'current_level']
            sess.create_advanced_sequence(sequence_name=sequenceName, property_names=properties_used, set_as_active_sequence=True)

            numCycle = len(df['vcc'])
            print(numCycle*1)
            for iCyc in range(numCycle):
                # for iPhase in range(1):
                sess.create_advanced_sequence_step(set_as_active_step=True)
                for sigName in df.columns:
                    if sigName=='#': continue
                    
                    # if sigName=='vcc':

                    val = df[sigName][iCyc]
                    


                    
                        
                    # print(sequenceName)
                    chnName = pinMap[sigName]
                    chn = sess.channels[f'{chnName}']
                    chn.output_function = nidcpower.OutputFunction.DC_VOLTAGE
                    # chn.voltage_level = float(val)s
                    chn.current_limit = 1e-3
                    chn.aperture_time = aperture_time
                    if val == '500uA':
                        chn.output_function = nidcpower.OutputFunction.DC_CURRENT
                        chn.current_level = 500e-6
                        chn.voltage_limit = 3
                        chn.voltage_limit_autorange = True
                        # chn.aperture_time = aperture_time

                    else:
                        if val == 1 or val == '1':
                            chn.output_function = nidcpower.OutputFunction.DC_VOLTAGE
                            chn.voltage_level = float(val)*3
                            chn.current_limit = 1e-3
                            # chn.aperture_time = aperture_time
                        else:
                            chn.voltage_level = float(val)
                            chn.current_limit = 1e-3


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
        for sequenceName in [self.dacVec]:
            session.active_advanced_sequence = sequenceName
            session.active_advanced_sequence_step = 0
            session.commit()

            with contextlib.ExitStack() as ctxt:

                for sigName in self.dictVec_df[sequenceName].columns:
                    if sigName=='#' or sigName=='vcc': continue

                    chnName = self.pinMap[sigName]
                    chn = session.channels[f'{chnName}']
                    ctxt.enter_context(chn.initiate())
                
                chnNameCK = self.pinMap['vcc']
                chnCK = session.channels[f'{chnNameCK}']
                ctxt.enter_context(chnCK.initiate())

                chnCK.wait_for_event(nidcpower.Event.SEQUENCE_ENGINE_DONE, timeout=timeout)
                # date = f"{str(time.localtime().tm_mon)}_{str(time.localtime().tm_mday)}_{str(time.localtime().tm_hour())}_{str(time.localtime().tm_min)}"
                with open(f'565_.csv', 'w', newline='') as fout:
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
    options = {'simulate': True, 'driver_setup': {'Model': '4163', 'BoardType': 'PXIe', }, }
    # for real runs
    #options = {}


    with nidcpower.Session(resource_name='SMU4163', options=options) as session:
        sram256bit.commonSetting(session)
        sram256bit.populate(session)
        

        dieXCoord = "x"
        dieYCoord = "y"
        sram256bit.testSRAM(session, dieXCoord, dieYCoord, out_dir)

