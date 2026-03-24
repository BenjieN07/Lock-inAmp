import numpy as np
from scipy.interpolate import interp1d
import pandas as pd
from numpy.polynomial import polynomial as P
import matplotlib.pyplot as plt

def getTdependentPosition(pospath, name, Trange=[], polyorder=2):

        """
        input a position vs Temperature coarse measurement (T(K), x(um), y(um), z(um))
        Fit the x,y,z positions and calcualte a finer position vs T data.
        Plot the result and save fitted result as txt with a '_fine' label
        Trange: if True, fit only over selected T range, e.g. Trange = [50,160]
        Note input Trange is from low to high
        """

        pos = pd.read_csv(pospath,sep='\t')

        fig,(ax1,ax2,ax3) = plt.subplots(1,3,constrained_layout=1,figsize=(9,4))
        ax1.scatter(pos['T'],pos[name + ' x(um)'],s=50,color='k')

        ax2.scatter(pos['T'],pos[name + ' y(um)'],s=50,color='k')

        ax3.scatter(pos['T'],pos[name + ' z(um)'],s=50,color='k')
        for ax,lb in zip([ax1,ax2,ax3],['x ($mu m$)','y ($mu m$)','z ($mu m$)']):
            ax.legend(['Data','Fit'], title=name)
            ax.set(xlabel='T (K)',ylabel=lb)

        # fit with linear or quadratic functions
        deg=polyorder  # or 2 for quadratic polynomial
        if len(Trange) > 0:
            Tmin = Trange[0]
            Tmax = Trange[1]
            pos.query('@Tmin < T < @Tmax',inplace=True)
        coeffx = P.polyfit(pos['T'],pos[name + ' x(um)'],deg=deg)
        coeffy = P.polyfit(pos['T'],pos[name + ' y(um)'],deg=deg)
        coeffz = P.polyfit(pos['T'],pos[name + ' z(um)'],deg=deg)
        moreT = np.arange(pos['T'].values[0],pos['T'].values[-1],-0.1)  # 0.1K step from highest to lowest temperature measured
        posx = P.Polynomial(coeffx)(moreT)
        posy = P.Polynomial(coeffy)(moreT)
        posz = P.Polynomial(coeffz)(moreT)
        ax1.plot(moreT,posx,'b--')
        ax2.plot(moreT,posy,'b--')
        ax3.plot(moreT,posz,'b--')
        pos_fitted = np.array([moreT,posx,posy,posz]).T
        fname = pospath.replace('.txt','_fitted.txt')
        np.savetxt(fname,pos_fitted,fmt='%.3f',delimiter='\t')
        plt.show()
        return pos_fitted

getTdependentPosition('Positions_295K-45K.txt', "sapphire", [40, 180])
