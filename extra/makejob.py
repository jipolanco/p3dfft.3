#!/usr/bin/python2

from fractions import Fraction
import math
import getopt
import sys
import os
import re

platforms = ["comet", "stampede"]

# job size
NUMNODES = 1		# --nodes
TASKSPERNODE = 16   # --ntasks-per-node

MT_NUMTHREADS = 2	  # env var OMP_NUM_THREADS
MT_RANKSPERNODE = 8	# used for dims

assert(MT_NUMTHREADS * MT_RANKSPERNODE == TASKSPERNODE)

def usage_exit(msg):
	print msg
	print "USAGE: ./configure.py -s comet|gordon|edison|cori|stampede [-m] [-p MINCORES MAXCORES [NUMTHREADS if -m is used] [MINGRID MAXGRID]]"
	print "Make sure to run this script from one level above your p3dfft.3 source directory!"
	print "-h displays usage information"
	print "-s  specifies which platform"
	print "-m  to build -mt branch"
	print "-p  to build performance test"
	sys.exit(1)

# Return list of all tests of this specific configuration
def gettests(mt, perf):
	p3dfft_dirs = next(os.walk('.'))[1]
	pattern = re.compile('p3dfft\+\+_compiled\S+')
	p3dfft_dirs = sorted(filter(pattern.match, p3dfft_dirs))
	pattern = re.compile('test_\S+_[cf]|cpp|iso')
	all_tests = []
	for p3dir in p3dfft_dirs:
		for root, _, files in os.walk(os.path.join(p3dir, 'sample')):
			if root == os.path.join(p3dir, 'sample'):
				continue
			all_tests += [os.path.abspath(os.path.join(root, f)) for f in filter(pattern.match, files)]
	return all_tests


# Get dimensions based on whether mt version or not
def getdims(mt):
	if mt:
		n = MT_RANKSPERNODE
	else:
		n = TASKSPERNODE
	dims = []
	facs = set(reduce(list.__add__,
		([i, n//i] for i in range(1, int(n**0.5) + 1) if n % i == 0)))
	facs = sorted(facs)
	if (len(facs) % 2 == 0):
					# take the two factors in the middle
		dims.append("'" + str(facs[len(facs)/2-1]) + " " + str(facs[len(facs)/2]) + "'")
	else:
		# perfect square, take the factor in the middle
		dims.append("'" + str(facs[len(facs)/2]) + " " + str(facs[len(facs)/2]) + "'")
	dims.append("'" + str(facs[len(facs)-1]) + " " + str(facs[0]) + "'")
	dims.append("'" + str(facs[0]) + " " +(facs[len(facs)-1]) + "'")
	return dims

# Standard test run line
def runline(platform, mt, basedir, test):
	if platform == "comet":
		if mt:
			return "ibrun --npernode " + str(MT_RANKSPERNODE) + " " + basedir + "/" + test + "\n"
		else:
			return "ibrun --npernode " + str(TASKSPERNODE * NUMNODES) + " " + basedir + "/" + test + "\n"
	elif platform == "stampede":
		if mt:
			return "ibrun -n " + str(MT_RANKSPERNODE) + " -o 0 tacc_affinity " + basedir + "/" + test + "\n"
		else:
			return "ibrun -n " + str(TASKSPERNODE * NUMNODES) + " -o 0 " + basedir + "/" + test + "\n"

# Test for 1x1 dims
def onebyone(platform, mt, basedir, test):
	if platform == "comet":
		return "ibrun --npernode 1 " + basedir + "/" + test + "\n"
	elif platform == "stampede":
		if mt:
			return "ibrun -n 1 -o 0 tacc_affinity " + basedir + "/" + test + "\n"
		else:
			return "ibrun -n 1 -o 0 " + basedir + "/" + test + "\n"

# Write all tests for all dims
def runall(platform, mt, perf, all_tests, all_dims, batchf):
	basedir = os.getcwd()
	for test in all_tests:
		if "cheby" in test:
			batchf.write("echo '32 32 33 2 1' > stdin\n")
		elif "many" in test:
			batchf.write("echo '32 32 32 2 5 1' > stdin\n")
		elif "pruned" in test:
			batchf.write("echo '64 64 64 32 32 32 2 1' > stdin\n")
		else:
			batchf.write("echo '32 32 32 2 1' > stdin\n")
		for dims in all_dims:
			# write dims
			batchf.write("echo " + dims + " > dims\n")
			# run test
			batchf.write(runline(platform, mt, basedir, test))
		# 1x1 dims test
		batchf.write("echo '1 1' > dims\n")
		batchf.write(onebyone(platform, mt, basedir, test))

def unevengrid(platform, mt, all_tests, all_dims, batchf):
	basedir = os.getcwd()
	for test in all_tests:
		if "cheby" in test:
			batchf.write("echo '14 26 38 2 1' > stdin\n")
		elif "many" in test:
			batchf.write("echo '14 26 38 2 5 1' > stdin\n")
		elif "pruned" in test:
			batchf.write("echo '64 64 64 32 32 32 2 1' > stdin\n")
		else:
			batchf.write("echo '14 26 38 2 1' > stdin\n")
		# write dims
		batchf.write("echo " + all_dims[0] + " > dims\n")
		# run test
		batchf.write(runline(platform, mt, basedir, test))

# Test for performance
def perftest(platform, mt, test, curr_numcores, num_threads):
	if platform == "comet":
		if mt:
			return "ibrun -n " + str(curr_numcores/num_threads) + " " + test + "\n"
		else:
			return "ibrun -N " + str(curr_numcores) + " " + test + "\n"
	elif platform == "stampede":
		if mt:
			return "ibrun -n " + str(curr_numcores/num_threads) + " -o 0 tacc_affinity " + test + "\n"
		else:
			return "ibrun -n " + str(curr_numcores) + " -o 0 " + test + "\n"

# Write all tests for performance testing
def runperf(platform, mt, perf, batchf, MINCORES, MAXCORES, MINGRID, MAXGRID, PERF_NUMTHREADS):
	# Get test_sine
	basedir = os.getcwd()
	p3dfft_dir = os.path.join(basedir, "p3dfft++_compiled_p_")
	f_test = os.path.join(p3dfft_dir, 'sample/C++/test_sin_cpp')

	# Run test_sine for all cores arranged in all dims
	curr_numcores = MINCORES
	while curr_numcores <= MAXCORES:
		# Calculate maximum grid size based on cores, and initialise grid size.
		NMAX = int(math.floor(math.pow(curr_numcores*4*math.pow(10,9)/48,Fraction(1,3))))
		if MINGRID > NMAX:
			print("MINGRID > NMAX")
			sys.exit(-1)

		curr_gridsize = MINGRID

		#while (curr_gridsize < NMAX)
		while curr_gridsize <= MAXGRID: # TODO: comment me out later
			batchf.write("echo '" + str(curr_gridsize) + " " + str(curr_gridsize) + " " + str(curr_gridsize) + " 2 5' > stdin\n")

			# Calculate dims
			all_dims = []
			all_dims.append("'16 " + str(int(curr_numcores/(16*PERF_NUMTHREADS))) + "'")
			all_dims.append("'32 " + str(int(curr_numcores/(32*PERF_NUMTHREADS))) + "'")
			all_dims.append("'64 " + str(int(curr_numcores/(64*PERF_NUMTHREADS))) + "'")
			#all_dims = ["'16 NUMCORES/16'", "'32 NUMCORES/32'", "'64 NUMCORES/64'"]

			for dims in all_dims:
				# write dims
				batchf.write("echo " + dims + " > dims\n")
				# run test
				batchf.write(perftest(platform, mt, f_test, curr_numcores, PERF_NUMTHREADS))
			curr_gridsize *= 2
		curr_numcores *= 2

def main():
	platform = None
	mt = False
	perf = False
	uneven = False
	email = ''
	perfopts = ""

	# parse command line options
	try:
		opts = getopt.getopt(sys.argv[1:], 's:e:hmp:u')
	except getopt.GetoptError as err:
		usage_exit(str(err))
	for o, a in opts[0]:
		if o == '-s':
			platform = a
		elif o == '-e':
			email = a
		elif o == '-h':
			usage_exit("**Help Message**")
		elif o == '-m':
			#mt = True
		elif o == '-p':
			perf = True
			perfopts = a
		elif o == '-u':
			uneven = True
		else:
			assert False, "unhandled option"
	if platform == None:
		usage_exit("no platform specified")
	elif platform not in platforms:
		usage_exit("invalid platform specified")

	if uneven and perf:
		usage_exit("no uneven grid performance tests")

	if perf:
		perfopts = perfopts.split()
		MINCORES = int(perfopts[0])
		MAXCORES = int(perfopts[1])
		if mt:
			if len(perfopts) != 3 and len(perfopts) != 5:
				usage_exit("num threads not specified")
			if len(perfopts) < 5:
				print("Using 1024^3 as default grid size.")
				MINGRID = 1024
				MAXGRID = 1024
			else:
				MINGRID = int(perfopts[3])
				MAXGRID = int(perfopts[4])
			PERF_NUMTHREADS = int(perfopts[2])
		else:
			if len(perfopts) < 4:
				print("Using 1024^3 as default grid size.")
				MINGRID = 1024
				MAXGRID = 1024
			else:
				MINGRID = int(perfopts[2])
				MAXGRID = int(perfopts[3])
			PERF_NUMTHREADS = 1

		if MINCORES > MAXCORES:
			print("MINCORES > MAXCORES")
			sys.exit(-1)
		if MINGRID > MAXGRID:
			print("MINGRID > MAXGRID")
			sys.exit(-1)

	# start write job	jobs/comet-p3dfft-mt.sh
	fname = "jobs/" + platform + "-" + "p3dfft++_compiled_p_" + ".sh"
	batchf = open(fname, 'w+')

	# write header
	batchf.write('#!/bin/bash\n')
	if platform == "comet":
		batchf.write('#SBATCH --job-name="' + "p3dfft++_compiled_p_" + '"\n')
		batchf.write('#SBATCH --output="out/out.%j"\n')
		batchf.write('#SBATCH --partition=compute\n')
		if perf:
			batchf.write('#SBATCH --nodes=' + str(int(MAXCORES/(32*PERF_NUMTHREADS))) + '\n')
			batchf.write('#SBATCH --ntasks-per-node=32\n')
		else:
			batchf.write('#SBATCH --nodes=' + str(NUMNODES) + '\n')
			batchf.write('#SBATCH --ntasks-per-node=' + str(TASKSPERNODE) + '\n')
		batchf.write('#SBATCH --export=ALL\n')
		batchf.write('#SBATCH --switches=1\n')
		if email:
			batchf.write('#SBATCH --mail-user=' + email + '\n')
			batchf.write('#SBATCH --mail-type=ALL\n')
		batchf.write('#SBATCH -t 01:00:00\n')
	elif platform == "stampede":
		batchf.write('#SBATCH -J ' + "p3dfft++_compiled_p_" + '\n')
		batchf.write('#SBATCH -o out/out.%j\n')
		batchf.write('#SBATCH -e out/out.%j\n')
		batchf.write('#SBATCH -p normal\n')
		if perf:
			batchf.write('#SBATCH -n' + str(MAXCORES/PERF_NUMTHREADS) + ' -N' + str(int(MAXCORES/(16*PERF_NUMTHREADS))) + '\n')
		else:
			if mt:
				batchf.write('#SBATCH -n' + str(MT_RANKSPERNODE) + ' -N' + str(NUMNODES) + '\n')
			else:
				batchf.write('#SBATCH -n ' + str(TASKSPERNODE) + ' -N' + str(NUMNODES) + '\n')
		if email:
			batchf.write('#SBATCH --mail-user=' + email + '\n')
			batchf.write('#SBATCH --mail-type=ALL\n')
		batchf.write('#SBATCH -t 01:00:00\n')
	batchf.write('\n')
	if mt:
		if perf:
			batchf.write('export OMP_NUM_THREADS=' + str(PERF_NUMTHREADS) + '\n')
		else:
			batchf.write('export OMP_NUM_THREADS=' + str(MT_NUMTHREADS) + '\n')

	if perf:
		runperf(platform, mt, perf, batchf, MINCORES, MAXCORES, MINGRID, MAXGRID, PERF_NUMTHREADS)
	else:
		all_tests = gettests(mt, perf)
		all_dims = getdims(mt)
		if uneven:
			unevengrid(platform, mt, all_tests, all_dims, batchf)
		else:
			runall(platform, mt, perf, all_tests, all_dims, batchf)

	# Close the file. Done.
	batchf.close()

	print "Wrote to " + fname

if __name__ == '__main__':
	main()

