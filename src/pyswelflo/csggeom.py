import pandas as pd
import numpy as np
import os

class CsgGeom:
    def __init__(self) -> None:
        '''
            Casing Geometry
            ---------------
            Casing geometry object for SwelFlo input.\n
            Example
            -------
            >>> csg = CsgGeom()
            >>> csg.add_section(
            >>>     elev=-9999,
            >>>     sec_len=1000,
            >>>     angle_vert=90,
            >>>     vert_ext=1000,
            >>>     subdiv_len=20,
            >>>     type='CASING',
            >>>     outerdiam=10.75
            >>> )
            >>> csg.add_section(
            >>>     elev=-9999,
            >>>     sec_len=1000,
            >>>     angle_vert=90,
            >>>     vert_ext=1000,
            >>>     subdiv_len=20,
            >>>     type='CASING',
            >>>     outerdiam=9.625
            >>> )
            >>> csg.pre_process_csggeom()
        '''
        self.df_casing = pd.DataFrame({
            'Elevation (mASL)':[],
            'Sec length (mMD)':[],
            'Angle to vertical (o)':[],
            'vertical extent (mTVD)':[],
            'Casing identifier':[],
            'radius (m)':[],
            'roughness (m)':[],
            'subdiv length (m)':[]
        })

    def check_csg(self,search_by='OUTERDIAM',val=4.5,type='CASING'):
        df = pd.read_csv('csg_lnr_db.csv')
        try:
            df = df[df[search_by] == val]
            df = df[df['CASINGLIN'].str.contains(type)]
        except:
            print(f'Error: No casing/liner available with {search_by}\'s value of {val}.')
        return df
    
    def download_csv_format(self,dir=os.getcwd()):
        '''
            Download default format for Casing Geometry in csv.
        '''
        self.add_section(
            elev=-9999,
            sec_len=1000,
            angle_vert=90,
            vert_ext=1000,
            subdiv_len=20,
            type='CASING',
            outerdiam=4.5
        )
        self.df_casing.to_csv(f'{dir}\\csggeom_format.csv',index=False)
    
    def pre_process_csggeom(self):
        df_casing = self.df_casing
        elev = df_casing['Elevation (mASL)'].values
        sec_len = df_casing['Sec length (mMD)'].values
        angle_vert = df_casing['Angle to vertical (o)'].values
        vert_ext = df_casing['vertical extent (mTVD)'].values
        csg_idfr = df_casing['Casing identifier'].values
        radius = df_casing['radius (m)'].values
        roughness = df_casing['roughness (m)'].values
        subdiv_len = df_casing['subdiv length (m)'].values
        n = len(elev)
        self.csggeom = 3*' '+f'{n}\n'
        for i in range(n):
            j = 3
            if elev[i] < 0:
                j = 2
            self.csggeom += j*' '+f'{elev[i]:.3f}        {sec_len[i]:.4f}       {angle_vert[i]:.8E}    {vert_ext[i]:.4f}         {int(csg_idfr[i])}    {radius[i]:.7f}       {roughness[i]:.7E}    {subdiv_len[i]:.5f}\n'
        self.csggeom = self.csggeom[:-1]

    def from_csv(self,filename,root=os.getcwd()):
        self.df_casing = pd.read_csv(root+'\\'+filename)

    def to_csv(self,filename,root=os.getcwd()):
        self.df_casing.to_csv(root+'\\'+filename,index=False)

    def add_section(self, **kwargs):
        '''
            Adding section of either casing or liner.\n
            Parameters
            -----------
            elev : float
                Elevation in mASL.
            sec_len : float
                Section length in mMD.
            angle_vert : float
                Angle to vertical in degrees.
            vert_ext : float
                Vertical extent in mTVD.
            subdiv_len : float
                Subdiv length in m.
            type : str
                Type either "CASING" or "LINER" or "OPEN HOLE".
            outerdiam : float
                Outer diameter of casing/liner section in in.
            roughness : float
                Roughness of casing/liner section in. 
        '''
        keys = list(kwargs.keys())
        if 'outerdiam' in keys:
            df = self.check_csg(
                search_by='OUTERDIAM',
                val=kwargs['outerdiam'],
                type=kwargs['type']
            )
            csg_idfr = df.index.values[0]+2
            radius = df['INNERDIAM'].values[0]*0.0254/2
            roughness = df['ROUGHNESS'].values[0]*0.0254

        self.df_casing.loc[len(self.df_casing.index)] = [
            kwargs['elev'],
            kwargs['sec_len'],
            kwargs['angle_vert'],
            kwargs['vert_ext'],
            csg_idfr,
            radius,
            roughness,
            kwargs['subdiv_len']
        ]