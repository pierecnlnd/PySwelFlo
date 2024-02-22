from pyXSteam.XSteam import XSteam
import pandas as pd
import numpy as np
import os

xst = XSteam(XSteam.UNIT_SYSTEM_MKS)

class Welllhead:
    def __init__(self) -> None:
        '''
            Feed Points
            ---------------
            Feed points object for SwelFlo input.\n
            Example
            -------
            >>> wh = Welllhead()
            >>> wh.add_cond(
            >>>     wh_p=8,
            >>>     wh_Q=20,
            >>>     wh_h_flo=921.43,
            >>>     wh_xCO2=0.001
            >>> )
            >>> wh.pre_process_wellhead()
        '''
        self.df_wh = pd.DataFrame({
            'P (Bara)':[],
            'Q (kg/s)':[],
            'T (oC)':[],
            'H (kJ/kg)':[],
            'flowing H (kJ/kg)':[],
            'X':[],
            'flowing X':[],
            'XCO2':[],
        })
    
    def download_csv_format(self,dir=os.getcwd()):
        '''
            Download default format for Feed Points in csv.
        '''
        self.add_cond(
            wh_p=8,
            wh_Q=20,
            wh_h_flo=921.43,
            wh_xCO2=0.001
        )
        self.df_wh.to_csv(f'{dir}\\csggeom_format.csv',index=False)
    
    def pre_process_wellhead(self):
        df_wh = self.df_wh
        wh_p = df_wh['P (Bara)'].values[0]
        wh_Q = df_wh['Q (kg/s)'].values[0]
        wh_T = df_wh['T (oC)'].values[0]
        wh_h = df_wh['H (kJ/kg)'].values[0]
        wh_h_flo = df_wh['flowing H (kJ/kg)'].values[0]
        wh_x = df_wh['X'].values[0]
        wh_x_flo = df_wh['flowing X'].values[0]
        wh_xCO2 = df_wh['XCO2'].values[0]
        self.wellhead = '   1\n   '+f'{wh_p*1.01e5:.4f}  '+\
            f'{wh_Q:.4f}  '+f'{wh_T:.4f}  '+\
            f'{wh_h:.4f}  '+f'{wh_h_flo*1e3:.4f}  '+\
            f'{wh_x:.4f}  '+f'{wh_x_flo:.5E}  '+\
            f'{wh_xCO2:.4f}  '

    def from_csv(self,filename,root=os.getcwd()):
        self.df_wh = pd.read_csv(root+'\\'+filename)

    def to_csv(self,filename,root=os.getcwd()):
        self.df_wh.to_csv(root+'\\'+filename,index=False)

    def add_cond(self, **kwargs):
        '''
            Add wellhead data.\n
            Parameters
            -----------
            wh_p : float
                Wellhead pressure at wellhead in bar.
            wh_Q : float
                Mass rate at wellhead in kg/s.
            wh_T : float, default=170
                Wellhead temperature at wellhead in deg-C.
            wh_h : float, default=838.9
                Wellhead enthalpy at wellhead in kJ/kg.
            wh_h_flo : float, default=921.43
                Flowing enthalpyat wellhead  in kJ/kg.
            wh_x : float, default=0.059
                Dryness at wellhead in fraction [0,1].
            wh_x_flo : float, default=0.1
                Flowing dryness at wellhead in fraction [0,1].
            wh_xCO2 : float, default=0.001
                CO2 fraction at wellhead [0,1]. 
        '''
        keys = list(kwargs.keys())
        if 'wh_p' in keys:
            if 'wh_T' in keys:
                kwargs['wh_h_flo'] = xst.h_pt(kwargs['wh_p'],kwargs['wh_T'])
                kwargs['wh_x_flo'] = xst.x_ph(kwargs['wh_p'],kwargs['wh_h_flo'])
            elif 'wh_h_flo' in keys:
                kwargs['wh_T'] = xst.t_ph(kwargs['wh_p'],kwargs['wh_h_flo'])
                kwargs['wh_x_flo'] = xst.x_ph(kwargs['wh_p'],kwargs['wh_h_flo'])
            elif 'wh_x_flo' in keys:
                kwargs['wh_h_flo'] = xst.h_px(kwargs['wh_p'],kwargs['wh_x_flo'])
                kwargs['wh_T'] = xst.t_ph(kwargs['wh_p'],kwargs['wh_h_flo'])

        self.df_wh.loc[len(self.df_wh.index)] = [
            kwargs['wh_p'],
            kwargs['wh_Q'],
            kwargs['wh_T'],
            -999,
            kwargs['wh_h_flo'],
            -999,
            kwargs['wh_x_flo'],
            kwargs['wh_xCO2'],
        ]