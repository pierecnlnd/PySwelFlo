import pandas as pd
import numpy as np
import os
import subprocess

ans_param = {
    'Topdown':1,
    'Bottomup':2
}
velt_param = {
    'Orkiszewski':1,
    'Armand':0,
    'Hadgu v only':2,
    'Hadgu full':3,
    'Duns & Ros v only':4,
    'Duns & Ros full':5,
    'Hagedorn & Brown':6
}
wantoutc_param = {
    True:1,
    False:0
}
allowhflo_param = {
    True:'T',
    False:'F'
}

class SWFinput:
    def __init__(self, **kwargs):
        '''
            Setup input for SwelFlo.\n
            Parameters
            -----------
            allowhflo : bool, default=False
                Allow heat flow to/from country.
            velt : str, default="Orkiszewski" 
                velt used "Orkiszewski"/"Armand"/"Hadgu v only"/"Hadgu full"\
                "Duns & Ros v only"/"Duns & Ros full"/"Hagedorn & Brown".
            text : list(str,str,str), default=['','','']
                Project descriptions consists of 3 lines.
            wantoutc : bool, default=True
                Producing output curve. 
            ans : str, default="Bottomup"
                Simulation direction either "Topdown" or "Bottomup".
            spacng : int, default=50
                Spacing for data output (m).
            oc_settings : dict
                Mandatory if wantoutc set to be True.
                - nsimvals : int, default=10
                - gotoutc : bool, default=True
                - qmaxoc : float, default=0 (kg/s)
                - qminoc : float, default=0 (kg/s)
                - nsimoutcpts : int, default=1
                - whptolerance : float, default=0.001 (bar)
                - pminset : float, default=0 (bar)
                - pmaxset : float, default=0 (bar)

            daltonR : float, default=0
            daltonRButton : int, default=1
            hwlbt : float, default=90
            xcwlbt : float, default=0.001
            chfelev : float, default=0
            wellhead : Wellhead
            csggeom : CsgGeom
            feedpts : FeedPts
        '''
        keys = list(kwargs.keys())

        try:
            self.text = kwargs['text'] 
            self.ans = ans_param[kwargs['ans']] 
            self.velt = velt_param[kwargs['velt']] 
            self.wantoutc = wantoutc_param[kwargs['wantoutc']]
            self.allowhflo = allowhflo_param[kwargs['allowhflo']]
            self.spacng = kwargs['spacng']
            self.daltonR = kwargs['daltonR']
            self.daltonRButton = kwargs['daltonRButton']
            self.hwlbt = kwargs['hwlbt']
            self.xcwlbt = kwargs['xcwlbt']
            self.chfelev = kwargs['chfelev']
        except:
            self.text = ['Template. used in absence of an input file. Prodn. flash in well.',
                         'One feed. topdown flow. Orkiszewski correlation. No output file asked for.',
                         'No reservoir T profile. one casing section 1000m vertical. Ready to run.'] 
            self.ans = 2 
            self.velt = 1
            self.wantoutc = 0 
            self.allowhflo = 'F'
            self.spacng = 50
            self.daltonR = 0
            self.daltonRButton = 1
            self.hwlbt = 90
            self.xcwlbt = 0.001
            self.chfelev = 0
        self.doublesim = 0.0
        self.gwellflag = 0
        self.simranok = 'T'
        if 'oc_settings' in keys:
            self.nsimvals = kwargs['oc_settings']['nsimvals']
            self.gotoutc = kwargs['oc_settings']['nsimvals']
            self.qmaxoc = kwargs['oc_settings']['qmaxoc']
            self.qminoc = kwargs['oc_settings']['qminoc']
            self.nsimoutcpts = kwargs['oc_settings']['nsimoutcpts']
            self.whptolerance = kwargs['oc_settings']['whptolerance']
            self.pminset = kwargs['oc_settings']['pminset']
            self.pmaxset = kwargs['oc_settings']['pmaxset']
        else:
            self.nsimvals = 10
            self.gotoutc = allowhflo_param[True]
            self.qmaxoc = 0
            self.qminoc = 0
            self.nsimoutcpts = 1
            self.whptolerance = 0.001
            self.pminset = 0
            self.pmaxset = 0            
        self.readytoplot = 'F' 
        self.getprofile = 'T' 
        
        self.wellhead = kwargs['wellhead'].wellhead
        self.csggeom = kwargs['csggeom'].csggeom
        self.length = kwargs['feedpts'].length
        self.feedpts = kwargs['feedpts'].feedpts
        self.rockprop = '   2.00000000000000\n   2800.00000000000\n   1000.00000000000\n   604800.000000000\n'
    
    def pre_process_swfinput(self):
        self.swfinput = ''
        self.swfinput += f'{self.text[0]}\n' # Line 1
        self.swfinput += f'{self.text[1]}\n' # Line 2
        self.swfinput += f'{self.text[2]}\n' # Line 3
        self.swfinput += f'   {self.ans}  {self.velt}  {self.nsimvals}  {self.wantoutc}'
        self.swfinput += f'  {self.doublesim:.6f} {self.gwellflag}  {self.simranok}'
        self.swfinput += f'  {self.gotoutc}  {self.readytoplot}  {self.getprofile}  {self.allowhflo}'
        self.swfinput += f'  {self.qmaxoc}  {self.qminoc}  {self.nsimoutcpts}  {self.spacng}'
        self.swfinput += f'  {self.daltonR}  {self.daltonRButton}  {self.hwlbt*1e3}  {self.xcwlbt:.5E}  {self.chfelev}\n'
        self.swfinput += '   0\n'
        self.swfinput += f'{self.wellhead}\n'
        self.swfinput += f'   {self.whptolerance:.15E} {self.pminset:.10E} {self.pmaxset:.10E}\n'
        self.swfinput += f'   {self.length:.10f}\n' 
        self.swfinput += self.rockprop 
        self.swfinput += f'{self.csggeom}\n'
        self.swfinput += '   0\n'
        self.swfinput += f'{self.feedpts}\n'
    
    def write_input(self,dir=os.getcwd()):
        with open(dir+'\\SWFinput.txt','w') as f:
            f.write(self.swfinput)
        
        self.current_dir = dir
    
    def run(self,root=os.getcwd()):
        subprocess.run([root+'\\swelflo.exe', '-s', '-f', self.current_dir+'\\SWFinput.txt','-p',self.current_dir])