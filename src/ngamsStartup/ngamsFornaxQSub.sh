#!/bin/bash

#PBS -l select=6:ncpus=12:ngpus=1:mem=2gb:mpiprocs=1
#PBS -l walltime=00:60:00
#PBS -m e
#PBS -q workq
#PBS -N NGAS_cluster
#PBS -A cwu-icrar
#PBS -W group_list=astronomy556
#PBS -o /home/cwu/ngas_run/run.out
#PBS -e /home/cwu/ngas_run/run.err

mpirun -np 6 /scratch/astronomy556/MWA/ngas_rt/bin/python /scratch/astronomy556/MWA/ngas_rt/src/ngamsStartup/ngamsFornaxMgr.py