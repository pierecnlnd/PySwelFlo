from pyXSteam.XSteam import XSteam
import pandas as pd
import numpy as np
import os

xst = XSteam(XSteam.UNIT_SYSTEM_MKS)

class FeedPts:
    def __init__(self) -> None:
        '''
            Feed Points
            ---------------
            Feed points object for SwelFlo input.\n
            Example
            -------
            >>> feed = FeedPts()
            >>> feed.add_points(
            >>>     depth=1000,
            >>>     type='fixed Q',
            >>>     res_p=55,
            >>>     res_T=270,
            >>>     res_xCO2=.3e-3,
            >>>     Q=27.075
            >>> )
            >>> feed.add_points(
            >>>     depth=1100,
            >>>     type='fixed Q',
            >>>     res_p=120,
            >>>     res_T=270,
            >>>     res_xCO2=.3e-3,
            >>>     Q=27.075
            >>> )
            >>> feed.pre_process_feedpts()
        '''
        self.df_feed = pd.DataFrame({
            'Depth (mMD)':[],
            'Type':[],
            'Res P (Bara)':[],
            'Res T (oC)':[],
            'Res H (kJ/kg)':[],
            'Res X':[],
            'Res XCO2':[],
            'sigma (1), Q(2,kg/s), C(3,4)':[],
            'A(1),n(3),d(4)':[]
        })
    
    def download_csv_format(self,dir=os.getcwd()):
        '''
            Download default format for Feed Points in csv.
        '''
        self.add_points(
            depth=1000,
            type='fixed Q',
            res_p=55,
            res_T=270,
            res_xCO2=.3e-3,
            Q=27.075
        )
        self.df_feed.to_csv(f'{dir}\\feedpts_format.csv',index=False)
    
    def pre_process_feedpts(self):
        df_feed = self.df_feed
        depth = df_feed['Depth (mMD)'].values
        col_0 = df_feed['Type'].values
        res_p = df_feed['Res P (Bara)'].values
        res_T = df_feed['Res T (oC)'].values
        res_h = df_feed['Res H (kJ/kg)'].values
        res_x = df_feed['Res X'].values
        res_xCO2 = df_feed['Res XCO2'].values
        col_1 = df_feed['sigma (1), Q(2,kg/s), C(3,4)'].values
        col_2 = df_feed['A(1),n(3),d(4)'].values
        self.length = np.nanmax(depth)
        n = len(depth)
        self.feedpts = 3*' '+f'{n}\n'
        for i in range(n):
            scol_1 = f'{col_1[i]:.5E}'
            if col_1[i] > 1:
                scol_1 = f'{col_1[i]:.4E}'

            try:
                scol_2 = f'{col_2[i]:.5E}'
                if col_2[i] > 1:
                    scol_2 = f'{col_2[i]:.4E}'
            except:
                scol_2 = col_2[i]
            
            res_p_i = f'{res_p[i]*1e5:.4E}'
            if len(f'{res_p[i]}') > 2:
                res_p_i = f'{res_p[i]*1e5:.3E}'
                
            self.feedpts += 3*' '+f'{depth[i]:.11f}  {int(col_0[i])}  {res_p_i}  {res_T[i]:.4E}  {res_h[i]*1e3:.4E}  {res_x[i]:.5E}  {res_xCO2[i]:.5E}  {scol_1}  {scol_2}\n'
        self.feedpts = self.feedpts[:-1]

    def from_csv(self,filename,root=os.getcwd()):
        self.df_feed = pd.read_csv(root+'\\'+filename)

    def to_csv(self,filename,root=os.getcwd()):
        self.df_feed.to_csv(root+'\\'+filename,index=False)

    def add_points(self, **kwargs):
        '''
            Adding feedzone points.\n
            Parameters
            -----------
            depth : float
                Depth in mMD.
            type : str
                Type of feedzone parameter either "prod index"/"fixed Q"/"dry steam"/"drawdown".
            res_p : float
                Reservoir pressure in bara.
            res_T : float
                Reservoir temperature in deg-C.
            res_h : float
                Reservoir enthalpy in kJ/kg.
            res_x : float
                Reservoir dryness in fraction [0,1].
            res_xCO2 : float
                Reservoir CO2 fraction in fraction [0,1].
            sigma : float
                Sigma (based on SwelFlo manual).
            Q : float
                Mass rate in kg/s(based on SwelFlo manual).
            C : float
                Constant C (based on SwelFlo manual).
            A : float
                Constant A (based on SwelFlo manual).
            n : float
                Constant n (based on SwelFlo manual).
            d : float
                Constant d (based on SwelFlo manual). 
        '''
        if kwargs['type'] == 'prod index':
            col_0 = 1
            col_1 = kwargs['sigma']
            col_2 = kwargs['A']
        elif kwargs['type'] == 'fixed Q':
            col_0 = 2
            col_1 = kwargs['Q']
            col_2 = ''
        elif kwargs['type'] == 'dry steam':
            col_0 = 3
            col_1 = kwargs['C']
            col_2 = kwargs['n']
        else:
            col_0 = 4
            col_1 = kwargs['C']
            col_2 = kwargs['d']
        
        keys = list(kwargs.keys())
        if 'res_p' in keys:
            if 'res_T' in keys:
                kwargs['res_h'] = xst.h_pt(kwargs['res_p'],kwargs['res_T'])
                kwargs['res_x'] = xst.x_ph(kwargs['res_p'],kwargs['res_h'])
            elif 'res_h' in keys:
                kwargs['res_T'] = xst.t_ph(kwargs['res_p'],kwargs['res_h'])
                kwargs['res_x'] = xst.x_ph(kwargs['res_p'],kwargs['res_h'])
            elif 'res_x' in keys:
                kwargs['res_h'] = xst.h_px(kwargs['res_p'],kwargs['res_x'])
                kwargs['res_T'] = xst.t_ph(kwargs['res_p'],kwargs['res_h'])

        self.df_feed.loc[len(self.df_feed.index)] = [
            kwargs['depth'],
            col_0,
            kwargs['res_p'],
            kwargs['res_T'],
            kwargs['res_h'],
            kwargs['res_x'],
            kwargs['res_xCO2'],
            col_1,
            col_2
        ]