import os, shutil
from nirc2.reduce import util
import asciidata
import numpy as np
import pyfits
from nirc2.reduce import nirc2_util
from nirc2.reduce import calibrate
from nirc2.reduce import align_rms
import subprocess
import pylab as py
import pdb

class Analysis(object):
    """
    Object that will perform our standard post-data-reduction analysis.
    This includes running starfinder, calibrating, and extracting positional
    and photometric errors via align_rms. 
    """

    def __init__(self, epoch, rootDir='/g/lu/data/orion/', filt='kp', 
                 epochDirSuffix=None, imgSuffix=None, stfDir=None,
                 useDistorted=False, cleanList='c.lis'):

        # Setup default parameters
        self.type = 'ao'
        self.corrMain = 0.8
        self.corrSub = 0.6
        self.corrClean = 0.7

        self.starlist = rootDir + 'source_list/psf_central.dat'
        self.labellist = rootDir+ 'source_list/label.dat'
        self.orbitlist = rootDir+ 'source_list/orbits.dat'
        self.calFile = rootDir + 'source_list/photo_calib.dat'
        
        self.calStars = ['16C', '16NW', '16CC']
        self.calFlags = '-f 1 -R '
        self.mapFilter2Cal = {'kp': 1, 'lp': 3, 'h': 4, 'ms': 5}
        if 'kp' in filt:
            self.calColumn = 1
        else: # case for Maser mosaic, deep mosaic
            self.calColumn = self.mapFilter2Cal[filt]
        self.calCooStar = '16C'
        
        self.cooStar = 'irs16C'

        self.deblend = None

        self.alignFlags = '-R 3 -v -p -a 0'

        self.numSubMaps = 3
        self.minSubMaps = 3
        
        # Setup input parameters 
        self.epoch = epoch

        self.rootDir = rootDir
        if not self.rootDir.endswith('/'):
            self.rootDir += '/'     

        self.filt = filt
        
        if epochDirSuffix != None:
            self.suffix = '_' + epochDirSuffix
        else:
            self.suffix = ''

        if imgSuffix != None:
            self.imgSuffix = '_' + imgSuffix
        else:
            self.imgSuffix = ''

        # Setup Directories
        self.dirEpoch = self.rootDir + self.epoch + self.suffix + '/'
        self.dirClean = self.dirEpoch + 'clean/' + self.filt + '/'
        if useDistorted:
            self.dirClean += 'distort/'
        if stfDir != None:
            self.dirCleanStf = self.dirClean + 'starfinder/' + stfDir + '/'
        else:
            self.dirCleanStf = self.dirClean + 'starfinder/'
        self.dirCleanAln = self.dirCleanStf + 'align/'

        self.dirCombo = self.dirEpoch + 'combo/'
        if stfDir != None:
            self.dirComboStf = self.dirCombo + 'starfinder/' + stfDir + '/'
        else:
            self.dirComboStf = self.dirCombo + 'starfinder/'
        self.dirComboAln = self.dirComboStf + 'align/'

        # make the directories if we need to
        if cleanList != None:
            util.mkdir(self.dirCleanStf)
            util.mkdir(self.dirCleanAln)
        util.mkdir(self.dirComboStf)
        util.mkdir(self.dirComboAln)

        # Get the list of clean files to work on
        self.cleanList = cleanList
        self.cleanFiles = []
        if cleanList != None:
            _list = asciidata.open(self.dirClean + self.cleanList, 'r')
            for ii in range(_list.nrows):
                fields = _list[0][ii].split('/')
                filename = fields[-1].replace('.fits', '')
                self.cleanFiles.append(filename)

        # Keep track of the current directory we started in
        self.dirStart = os.getcwd()

    def analyzeCombo(self):
        self.starfinderCombo()
        self.calibrateCombo()
        self.alignCombo()

    def analyzeClean(self):
        self.starfinderClean()
        self.calibrateClean()
        self.alignClean()

    def analyzeComboClean():
        self.starfinderCombo()
        self.starfinderClean()
        self.calibrateCombo()
        self.calibrateClean()
        self.alignCombo()
        self.alignClean()


    def starfinderCombo(self, oldPsf=False):
        try:
            print 'COMBO starfinder'
            print 'Coo Star: ' + self.cooStar
            
            os.chdir(self.dirComboStf)
            
            if self.type == 'ao':
                # Write an IDL batch file
                fileIDLbatch = 'idlbatch_combo_' + self.filt
                fileIDLlog = fileIDLbatch + '.log'
                util.rmall([fileIDLlog, fileIDLbatch])

                _batch = open(fileIDLbatch, 'w')
                _batch.write("find_stf_new, ")
                _batch.write("'" + self.epoch + "', ")
                _batch.write("'" + self.filt + "', ")
                _batch.write("corr_main='%3.1f', " % self.corrMain)
                _batch.write("corr_subs='%3.1f', " % self.corrSub)
                # Only send in the deblend flag if using it!
                if self.deblend != None:
                    _batch.write("deblend='" + str(self.deblend) + "', ")
                _batch.write("cooStar='" + self.cooStar + "', ")
                _batch.write("suffixEpoch='" + self.suffix + "', ")
                _batch.write("imgSuffix='" + self.imgSuffix + "', ")
                _batch.write("starlist='" + self.starlist + "', ")
                if oldPsf:
                    _batch.write("/oldPsf, ")
                
                _batch.write("rootDir='" + self.rootDir + "'")
                _batch.write("\n")
                _batch.write("exit\n")
                _batch.close()
            elif self.type == 'speckle':
                fileIDLbatch = 'idlbatch_combo' 
                fileIDLlog = fileIDLbatch + '.log'
                util.rmall([fileIDLlog, fileIDLbatch])
                
                _batch = open(fileIDLbatch, 'w')
                _batch.write("find_new_speck, ")
                _batch.write("'" + self.epoch + "', ")
                _batch.write("corr_main='%3.1f', " % self.corrMain)
                _batch.write("corr_subs='%3.1f', " % self.corrSub)
                _batch.write("starlist='" + self.starlist + "', ")
                if oldPsf:
                    _batch.write("/oldPsf, ")
                _batch.write("rootDir='" + self.rootDir + "'")
                _batch.write("\n")
                _batch.write("exit\n")
                _batch.close()
            
            cmd = 'idl < ' + fileIDLbatch + ' >& ' + fileIDLlog            
            #os.system(cmd)
            subp = subprocess.Popen(cmd, shell=True, executable="/bin/tcsh")
            tmp = subp.communicate()

            # Copy over the PSF starlist that was used (for posterity).
            outPsfs = 'mag%s%s_%s_psf_list.txt' % (self.epoch, self.imgSuffix, self.filt)
            shutil.copyfile(self.starlist, outPsfs)

            os.chdir(self.dirStart)
        except:
            os.chdir(self.dirStart)
            raise
            
        
    def starfinderClean(self):
        try:
            print 'CLEAN starfinder'
            
            os.chdir(self.dirCleanStf)
            
            # Write an IDL batch file
            fileIDLbatch = 'idlbatch_clean_' + self.filt
            fileIDLlog = fileIDLbatch + '.log'
            util.rmall([fileIDLlog, fileIDLbatch])
            
            _batch = open(fileIDLbatch, 'w')
            _batch.write("find_stf_clean, ")
            _batch.write("'" + self.epoch + "', ")
            _batch.write("'" + self.filt + "', ")
            _batch.write("corr='" + str(self.corrClean) + "', ")
            _batch.write("cooStar='" + self.cooStar + "', ")
            _batch.write("suffixEpoch='" + self.suffix + "', ")
            _batch.write("starlist='" + self.starlist + "', ")
            _batch.write("fileList='" + self.cleanList + "', ")
            _batch.write("rootDir='" + self.rootDir + "'")
            _batch.write("\n")
            _batch.write("exit\n")
            _batch.close()
            
            cmd = 'idl < ' + fileIDLbatch + ' >& ' + fileIDLlog
            #os.system(cmd)
            subp = subprocess.Popen(cmd, shell=True, executable="/bin/tcsh")
            tmp = subp.communicate()
            
            # Copy over the PSF starlist that was used (for posterity).
            outPsfs = 'c_%s_%s_psf_list.txt' % (self.epoch, self.filt)
            shutil.copyfile(self.starlist, outPsfs)
            
            os.chdir(self.dirStart)
        except:
            os.chdir(self.dirStart)
            raise

    def calibrateCombo(self):
        try:
            print 'COMBO calibrate'
            
            # Get the position angle from the *.fits header
            # We assume that the submaps have the same PA as the main maps
            os.chdir(self.dirCombo)

            calCamera = 1
            if self.type == 'ao':
                fitsFile = 'mag%s%s_%s.fits' % (self.epoch, self.imgSuffix, self.filt)
                angle = float(pyfits.getval(fitsFile, 'ROTPOSN')) - 0.7
                
                # Check for wide camera
                calCamera = calibrate.get_camera_type(fitsFile)
            elif self.type == 'speckle':
                angle = 0.0
                fitsFile = 'mag%s.fits' % self.epoch

            
            # CALIBRATE
            os.chdir(self.dirComboStf)

            cmd = 'calibrate_new %s' % self.calFlags
            cmd += '-T %.1f ' % angle
            cmd += '-I %s ' % self.calCooStar
            cmd += '-N %s ' % self.calFile
            cmd += '-M %d ' % self.calColumn
            cmd += '-c %d ' % calCamera
            if (self.calStars != None) and (len(self.calStars) > 0):
                cmd += '-S '
                for cc in range(len(self.calStars)):
                    if (cc != 0):
                        cmd += ','
                    cmd += self.calStars[cc]
            cmd += ' '

            # Calibrate Main Map
            if self.type == 'speckle':   # This stuff is left over.
                fileMain = 'mag%s_%3.1f_stf.lis' % \
                (self.epoch, self.corrMain)
            else:
                if self.deblend == 1:
                    fileMain = 'mag%s%s_%s_%3.1fd_stf.lis' % \
                    (self.epoch, self.imgSuffix, self.filt, self.corrMain)
                else:
                    fileMain = 'mag%s%s_%s_%3.1f_stf.lis' % \
                    (self.epoch, self.imgSuffix, self.filt, self.corrMain)
            print cmd + fileMain

            # Now call from within python... don't bother with command line anymore.
            argsTmp = cmd + fileMain
            args = argsTmp.split()[1:]
            calibrate.main(args)

            # Copy over the calibration list.
            shutil.copyfile(self.calFile, fileMain.replace('.lis', '_cal_phot_list.txt'))
            
            # Calibrate Sub Maps
            for ss in range(self.numSubMaps):
                if self.type == 'speckle':
                    fileSub = 'm%s_%d_%3.1f_stf.lis' % \
                        (self.epoch, ss+1, self.corrSub)
                else:
                    if self.deblend == 1:
                        fileSub = 'm%s%s_%s_%d_%3.1fd_stf.lis' % \
                        (self.epoch, self.imgSuffix, self.filt, ss+1, self.corrSub)
                    else:
                        fileSub = 'm%s%s_%s_%d_%3.1f_stf.lis' % \
                        (self.epoch, self.imgSuffix, self.filt, ss+1, self.corrSub)

                print cmd + fileSub
                
                argsTmp = cmd + fileSub
                args = argsTmp.split()[1:]
                calibrate.main(args)

            os.chdir(self.dirStart)
        except:
            os.chdir(self.dirStart)
            raise

    def calibrateClean(self):
        try:
            # Calibrate each file
            os.chdir(self.dirCleanStf)
            print "DEBUG 2nd dec --",self.dirCleanStf
            # open writeable file for log
            _log = open('calibrate.log','w')


            cmdBase = 'calibrate_new %s ' % self.calFlags
            cmdBase += '-I %s ' % self.calCooStar
            cmdBase += '-N %s ' % self.calFile
            cmdBase += '-M %d ' % self.calColumn
            if (self.calStars != None) and (len(self.calStars) > 0):
                cmdBase += '-S '
                for cc in range(len(self.calStars)):
                    if (cc != 0):
                        cmdBase += ','
                    cmdBase += self.calStars[cc]
            cmdBase += ' '

            for file in self.cleanFiles:
                fitsFile = '../%s.fits' % file
                listFile = '%s_%3.1f_stf.lis' % (file, self.corrClean)

                # Get the position angle
                angle = float(pyfits.getval(fitsFile, 'ROTPOSN')) - 0.7
                calCamera = calibrate.get_camera_type(fitsFile)

                cmd = cmdBase + ('-T %.1f -c %d ' % (angle, calCamera))

                cmd += listFile

                # 2nd dec 2009 - changed "_out" "_log"
                _log.write(cmd + '\n')

                args = cmd.split()[1:]
                calibrate.main(args)

            _log.close()  # clean up

            # Copy over the calibration list.
            shutil.copyfile(self.calFile, 'clean_phot_list.txt')
            
            os.chdir(self.dirStart)
        except:
            os.chdir(self.dirStart)
            raise

    def alignCombo(self):
        print 'ALIGN_RMS combo'

        if self.type == 'ao':
            file_ext = '_' + self.filt
        else:
            file_ext = self.filt

        try:
            os.chdir(self.dirCombo)
            # Get the align data type
            if self.type == 'ao':
                fitsFile = 'mag%s%s_%s.fits' % (self.epoch, self.imgSuffix, self.filt)
            elif self.type == 'speckle':
                fitsFile = 'mag%s.fits' % self.epoch
            alignType = nirc2_util.get_align_type(fitsFile, errors=False)


            os.chdir(self.dirComboAln)

            # Put the files in to the align*.list file
            alnList1 = 'align%s%s_%3.1f.list' % (self.imgSuffix, file_ext, self.corrMain)
            alnList2 = 'align%s%s_%3.1f_named.list' % (self.imgSuffix, file_ext, self.corrMain)


            _list = open(alnList1, 'w')
            if self.deblend == 1:
                _list.write('../mag%s%s%s_%3.1fd_stf_cal.lis %d ref\n' %
                            (self.epoch, self.imgSuffix, file_ext, self.corrMain, alignType))
            else:
                _list.write('../mag%s%s%s_%3.1f_stf_cal.lis %d ref\n' %
                            (self.epoch, self.imgSuffix, file_ext, self.corrMain, alignType))
            for ss in range(self.numSubMaps):
                if self.deblend == 1:
                    _list.write('../m%s%s%s_%d_%3.1fd_stf_cal.lis %d\n' %
                                (self.epoch, self.imgSuffix, file_ext, ss+1, self.corrSub, alignType))
                else:
                    _list.write('../m%s%s%s_%d_%3.1f_stf_cal.lis %d\n' %
                                (self.epoch, self.imgSuffix, file_ext, ss+1, self.corrSub, alignType))

                    
            _list.close()

            shutil.copyfile(alnList1, alnList2)

            # Make an unlabeled version
            cmd = 'java -Xmx1024m align %s ' % (self.alignFlags)
            cmd += '-r align%s%s_%3.1f ' % (self.imgSuffix, file_ext, self.corrMain)
            cmd += alnList1
            print cmd
            #os.system(cmd)
            subp = subprocess.Popen(cmd, shell=True, executable="/bin/tcsh")
            tmp = subp.communicate()

            # Make a named/labeled version
            cmd = 'java -Xmx1024m align %s ' % (self.alignFlags)
            cmd += '-N %s ' % self.labellist
            if (self.orbitlist != None) and (self.orbitlist != ''):
                cmd += '-o %s ' % self.orbitlist
            cmd += '-r align%s%s_%3.1f_named ' % (self.imgSuffix, file_ext, self.corrMain)
            cmd += alnList2
            print cmd

            subp = subprocess.Popen(cmd, shell=True, executable="/bin/tcsh")
            tmp = subp.communicate()


            align_options = 'align%s%s_%3.1f %d -e' % \
              (self.imgSuffix, file_ext, self.corrMain, self.minSubMaps)
            align_rms.run(align_options.split())

            align_options = 'align%s%s_%3.1f_named %d -e' % \
              (self.imgSuffix, file_ext, self.corrMain, self.minSubMaps)
            align_rms.run(align_options.split())


            # Move the resulting files to their final resting place
            os.rename('align%s%s_%3.1f_rms.lis' % 
                      (self.imgSuffix, file_ext, self.corrMain),
                      '../mag%s%s%s_rms.lis' % 
                      (self.epoch, self.imgSuffix, file_ext))
            os.rename('align%s%s_%3.1f_named_rms.lis' % 
                      (self.imgSuffix, file_ext, self.corrMain),
                      '../mag%s%s%s_rms_named.lis' % 
                      (self.epoch, self.imgSuffix, file_ext))

            # Copy over the label.dat and orbit.dat file that was used.
            shutil.copyfile(self.labellist,
                            'align%s%s_%3.1f_named_label_list.txt' % 
                            (self.imgSuffix, file_ext, self.corrMain))
                            
            if (self.orbitlist != None) and (self.orbitlist != ''):
                shutil.copyfile(self.orbitlist,
                                'align%s%s_%3.1f_named_orbit_list.txt' % 
                                (self.imgSuffix, file_ext, self.corrMain))

            # Now plot up the results
            plotSuffix = self.imgSuffix + file_ext
            os.chdir(self.dirComboStf)
            plotPosError('mag%s%s%s_rms.lis' % (self.epoch, self.imgSuffix, file_ext),
                         raw=True, suffix=plotSuffix)

            os.chdir(self.dirStart)
        except:
            os.chdir(self.dirStart)
            raise

    
    def alignClean(self):
        try:
            os.chdir(self.dirClean)

            # Get the align data type
            fitsFile = self.cleanFiles[0] + '.fits'
            alignType = nirc2_util.get_align_type(fitsFile, errors=False)
            alignCombo = alignType + 1

            # Make the align*.list file
            os.chdir(self.dirCleanAln)
            alnList = 'align_%s%s_%3.1f.list' % (self.imgSuffix, self.filt, self.corrClean)
            _list = open(alnList, 'w')

            # copy main map into it
            _list.write('%smag%s%s_%s_rms.lis %d ref\n' % 
                        (self.dirComboStf, self.epoch, self.imgSuffix, self.filt, alignCombo))
            # Add each clean file
            for ff in self.cleanFiles:
                _list.write('../%s_%3.1f_stf_cal.lis %d\n' %
                            (ff, self.corrClean, alignType))
            _list.close()

            # Run align
            cmd = 'java -Xmx1024m align %s ' % (self.alignFlags)
            cmd += '-N %s ' % self.labellist
            if (self.orbitlist != None) and (self.orbitlist != ''):
                cmd += '-o %s ' % self.orbitlist
            cmd += '-r align_%s%s_%3.1f_named ' % (self.imgSuffix, self.filt, self.corrClean)
            cmd += alnList

            #os.system(cmd)
            subp = subprocess.Popen(cmd, shell=True, executable="/bin/tcsh")
            tmp = subp.communicate()


            # Copy over the label.dat file that was used.
            shutil.copyfile(self.labellist,
                            'align_%s%s_%3.1f_named_label_list.txt' % 
                            (self.imgSuffix, self.filt, self.corrClean))
            if (self.orbitlist != None) and (self.orbitlist != ''):
                shutil.copyfile(self.orbitlist,
                                'align_%s%s_%3.1f_named_orbit_list.txt' % 
                                (self.imgSuffix, self.filt, self.corrClean))
                            
            os.chdir(self.dirStart)
        except:
            os.chdir(self.dirStart)
            raise
    




        


def plotPosError(starlist, raw=False, suffix='', radius=4, magCutOff=15.0,
                 title=True):
    """
    Make three standard figures that show the data quality 
    from a *_rms.lis file. 

    1. astrometric error as a function of magnitude.
    2. photometric error as a function of magnitude.
    3. histogram of number of stars vs. magnitude.

    Use raw=True to plot the individual stars in plots 1 and 2.
    """
    # Load up the starlist
    lis = asciidata.open(starlist)

    # Assume this is NIRC2 data.
    scale = 0.00995
    
    name = lis[0]._data
    mag = lis[1].tonumpy()
    x = lis[3].tonumpy()
    y = lis[4].tonumpy()
    xerr = lis[5].tonumpy()
    yerr = lis[6].tonumpy()
    snr = lis[7].tonumpy()
    corr = lis[8].tonumpy()

    merr = 1.086 / snr

    # Convert into arsec offset from field center
    # We determine the field center by assuming that stars
    # are detected all the way out the edge.
    xhalf = x.max() / 2.0
    yhalf = y.max() / 2.0
    x = (x - xhalf) * scale
    y = (y - yhalf) * scale
    xerr *= scale * 1000.0
    yerr *= scale * 1000.0

    r = np.hypot(x, y)
    err = (xerr + yerr) / 2.0

    magStep = 1.0
    radStep = 1.0
    magBins = np.arange(10.0, 20.0, magStep)
    radBins = np.arange(0.5, 9.5, radStep)
    
    errMag = np.zeros(len(magBins), float)
    errRad = np.zeros(len(radBins), float)
    merrMag = np.zeros(len(magBins), float)
    merrRad = np.zeros(len(radBins), float)

    ##########
    # Compute errors in magnitude bins
    ########## 
    #print '%4s  %s' % ('Mag', 'Err (mas)')
    for mm in range(len(magBins)):
        mMin = magBins[mm] - (magStep / 2.0)
        mMax = magBins[mm] + (magStep / 2.0)
        idx = (np.where((mag >= mMin) & (mag < mMax) & (r < radius)))[0]

        if (len(idx) > 0):
            errMag[mm] = np.median(err[idx])
            merrMag[mm] = np.median(merr[idx])
        
        #print '%4.1f  %5.2f' % (magBins[mm], errMag[mm])
        
                       
    ##########
    # Compute errors in radius bins
    ########## 
    for rr in range(len(radBins)):
        rMin = radBins[rr] - (radStep / 2.0)
        rMax = radBins[rr] + (radStep / 2.0)
        idx = (np.where((r >= rMin) & (r < rMax) & (mag < magCutOff)))[0]

        if (len(idx) > 0):
            errRad[rr] = np.median(err[idx])
            merrRad[rr] = np.median(err[idx])

    idx = (np.where((mag < magCutOff) & (r < radius)))[0]
    errMedian = np.median(err[idx])
    numInMedian = len(idx)

    ##########
    #
    # Plot astrometry errors
    #
    ##########
 
    # Remove figures if they exist -- have to do this
    # b/c sometimes the file won't be overwritten and
    # the program crashes saying 'Permission denied'
    if os.path.exists('plotPosError%s.png' % suffix):
        os.remove('plotPosError%s.png' % suffix)
    if os.path.exists('plotMagError%s.png' % suffix):
        os.remove('plotMagError%s.png' % suffix)
    if os.path.exists('plotNumStars%s.png' % suffix):
        os.remove('plotNumStars%s.png' % suffix)

    if os.path.exists('plotPosError%s.eps' % suffix):
        os.remove('plotPosError%s.eps' % suffix)
    if os.path.exists('plotMagError%s.eps' % suffix):
        os.remove('plotMagError%s.eps' % suffix)
    if os.path.exists('plotNumStars%s.eps' % suffix):
        os.remove('plotNumStars%s.eps' % suffix)

    py.figure(figsize=(6,6))
    py.clf()
    py.subplots_adjust(left=0.15, top=0.92, right=0.95)
    if (raw == True):
        idx = (np.where(r < radius))[0]
        py.semilogy(mag[idx], err[idx], 'k.')
        
    py.semilogy(magBins, errMag, 'g.-', lw=2)
    py.axis([8, 22, 1e-2, 30.0])
    py.xlabel('K Magnitude for r < %4.1f"' % radius, fontsize=16)
    py.ylabel('Positional Uncertainty (mas)', fontsize=16)
    if title == True:
        py.title(starlist)
    
    py.savefig('plotPosError%s.png' % suffix)
    py.savefig('plotPosError%s.eps' % suffix)

    ##########
    #
    # Plot photometry errors
    #
    ##########
    py.clf()
    if (raw == True):
        idx = (np.where(r < radius))[0]
        py.plot(mag[idx], merr[idx], 'k.')
        
    py.plot(magBins, merrMag, 'g.-')
    py.axis([8, 22, 0, 0.15])
    py.xlabel('K Magnitude for r < %4.1f"' % radius)
    py.ylabel('Photo. Uncertainty (mag)')
    py.title(starlist)
    
    py.savefig('plotMagError%s.png' % suffix)
    py.savefig('plotMagError%s.eps' % suffix)

    ##########
    # 
    # Plot histogram of number of stars detected
    #
    ##########
    py.clf()
    idx = (np.where(r < radius))[0]
    (n, bb, pp) = py.hist(mag[idx], bins=np.arange(9, 22, 0.5))
    py.xlabel('K Magnitude for r < %4.1f"' % radius)
    py.ylabel('Number of Stars')

    py.savefig('plotNumStars%s.png' % suffix)
    py.savefig('plotNumStars%s.eps' % suffix)

    # Find the peak of the distribution
    maxHist = n.argmax()
    maxBin = bb[maxHist]


    ##########
    # 
    # Save relevant numbers to an output file.
    #
    ##########
    # Print out some summary information
    print 'Number of detections: %4d' % len(mag)
    print 'Median Pos Error (mas) for K < %2i, r < %4.1f (N=%i):  %5.2f' % \
          (magCutOff, radius, numInMedian, errMedian)
    print 'Median Mag Error (mag) for K < %2i, r < %4.1f (N=%i):  %5.2f' % \
          (magCutOff, radius, numInMedian, np.median(merr[idx]))
    print 'Turnover mag = %4.1f' % (maxBin)


    out = open('plotPosError%s.txt' % suffix, 'w')
    out.write('Number of detections: %4d\n' % len(mag))
    out.write('Median Pos Error (mas) for K < %2i, r < %4.1f (N=%i):  %5.2f\n' % \
          (magCutOff, radius, numInMedian, errMedian))
    out.write('Median Mag Error (mag) for K < %2i, r < %4.1f (N=%i:  %5.2f\n' % \
          (magCutOff, radius, numInMedian, np.median(merr[idx])))
    out.write('Turnover mag = %4.1f\n' % (maxBin))
    out.close()
    


       

