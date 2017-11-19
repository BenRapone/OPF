from numpy import *
import scipy.io as sio
import sys
import time
import cplex
import copy

casenumber = 57
# file1 = "Qscase"+str(casenumber)+".mat";
# file2 = "Acase"+str(casenumber)+".mat";
# file3 = "bcase"+str(casenumber)+".mat";
# num_cores = multiprocessing.cpu_count()
bsteps = [0.001]
# bsteps = [0.005]
# bsteps = [0.01]

file1 = "C:/Users/Ben Rapone/Documents/Research/OPF/PNNL/DJRepo/ccsi-robustoptfeas/Ben/Code/src/Qscase"+str(casenumber)+".mat";
file2 = "C:/Users/Ben Rapone/Documents/Research/OPF/PNNL/DJRepo/ccsi-robustoptfeas/Ben/Code/src/Acase"+str(casenumber)+".mat";
file3 = "C:/Users/Ben Rapone/Documents/Research/OPF/PNNL/DJRepo/ccsi-robustoptfeas/Ben/Code/src/bcase"+str(casenumber)+".mat";

outfile = "CS"+str(casenumber)+"PythonUppLinInFeasBR"+str(bsteps[0])+".csv"
logfile = "CS"+str(casenumber)+"PythonUppLinInFeasBR"+str(bsteps[0])+"log.csv"

Qs = sio.loadmat(file1,variable_names="Qs")['Qs']
A = sio.loadmat(file2,variable_names="A")['A']
# b = sio.loadmat(file3,variable_names="b")['b']
b= 0.01*ones(shape(A)[0])

dim = int(shape(Qs)[2])
Q = {}
q = {}
c = {}

for k in range(0,dim):
    Q[k] = Qs[1:,1:,k]
    q[k] = 2*Qs[1:,:1,k]
    c[k] = Qs[0,0,k]

x = transpose(matrix(zeros(shape(Q[0])[1])))

# #### Perform Check

for k in range(0,dim):
  if 0 <= (transpose(x)*Q[k]*x)[0]+(transpose(x)*q[k])[0]+c[k]-10.0**(-4.0) and 0 >= (transpose(x)*Q[k]*x)[0]+(transpose(x)*q[k])[0]+c[k]+10.0**(-4.0):
    print "System not stable"

if casenumber <= 100:
    clist = [x for x in range(5)]
else:
    clist = [x for x in range(10)]

ceps = 10.0**(-6.0)
clb = {}
cub = {}

for k in range(dim):
  if k in clist:
      clb[k] = c[k]-ceps-0.0001
      cub[k] = c[k]+ceps+0.0001
  else:
      clb[k] = c[k]
      cub[k] = c[k]

nclist = range(dim)
for i in clist:
	nclist.remove(i)

##### Find maximal c choice

orig_stdout = sys.stdout
f = file(outfile,'w')
sys.stdout = f
print "Case"+ str(casenumber)+"Linear Constraints using python code, no SDP and uptri vars."
print "B, CRad, Time"
sys.stdout = orig_stdout
f.close()
orig_stdout = sys.stdout
f = file(logfile,'w')
sys.stdout = f
print "Case"+ str(casenumber)+"Linear Constraints using python code, no SDP and uptri vars."
sys.stdout = orig_stdout
f.close()

######## Basic Model Setup

## Model parameters
Gaplim = 0.0
prob = cplex.Cplex();
# prob.parameters.timelimit.set(timelim);
# prob.parameters.mip.limits.solutions.set(Solim);
# prob.parameters.mip.tolerances.integrality.set(0);
# prob.parameters.mip.tolerances.mipgap.set(Gaplim);
prob.objective.set_sense(prob.objective.sense.maximize);
prob.parameters.emphasis.mip.set(1) ## Emphasis set to 1 for Feasibility instead of 0 for balanced


## Model variables
newb = b.copy()
m = shape(A)[0]
n = shape(A)[1]
numvars = int(n*(n+1)/2.0+n)
numuptri = numvars-n
constraintrowindex = 0
CIndex = {}
xindices = prob.variables.add(names = ["x"+str(i) for i in range(numvars)])  ### XQ+Xq, first n^2 terms part of XQ, last Xq
for x in range(numvars):
    prob.variables.set_lower_bounds(x, -cplex.infinity)


### Create Upper Triangular dictionary 
UpTriDic = {}
counter = 0
for i in range(n):
	for j in range(i,n):
		UpTriDic[i,j] = counter
		UpTriDic[j,i] = counter
		counter += 1


### Constraint Ax<=b  
my_rhs = newb
prob.linear_constraints.add(rhs=my_rhs)
for L in range(m):
	x = constraintrowindex
	constraintrowindex += 1
	CIndex["axb",L] = x
	prob.linear_constraints.set_senses(x,"L")
	for R in range(n):
		y = numuptri + R 
		v = A[L,R]
		prob.linear_constraints.set_coefficients(x,y,v)


## Constraint -Axb^T-b(Ax)^T+AXA^T >= -bb
for L in range(m):
	for K in range(m):
		x = constraintrowindex
		constraintrowindex += 1
		CIndex["axa",L,K] = x
		my_rhs = [-1*newb[L]*newb[K]]
		prob.linear_constraints.add(rhs=my_rhs)
		prob.linear_constraints.set_senses(x, "G")
		for r in range(n):
			y = numuptri + r
			v = -(A[L,r]*newb[K]+newb[L]*A[K,r])
			prob.linear_constraints.set_coefficients(x,y,v)
			for s in range(r,n):
				y = UpTriDic[r,s]
				if r != s:
					v = A[K,s]*A[L,r]+A[K,r]*A[L,s]
				else:
					v = A[K,s]*A[L,r]
				prob.linear_constraints.set_coefficients(x,y,v)

## Tr(QX) + q^tx <=/>= -clb/-cub

for k in clist:
	x = constraintrowindex
	constraintrowindex += 1
	CIndex["qxcl", k] = x
	my_rhs = [-1*clb[k]]
	prob.linear_constraints.add(rhs=my_rhs)
	prob.linear_constraints.set_senses(x, "L")
	x = constraintrowindex
	constraintrowindex += 1
	CIndex["qxcu", k] = x
	my_rhs = [-1*cub[k]]
	prob.linear_constraints.add(rhs=my_rhs)
	prob.linear_constraints.set_senses(x, "G")
	for r in range(n):
		y = numuptri + r
		v = q[k][r,0]
		prob.linear_constraints.set_coefficients(x-1,y,v)
		prob.linear_constraints.set_coefficients(x,y,v)
		for s in range(r,n):
			y = UpTriDic[r,s]
			if r!=s:
				v = Q[k][r,s]+Q[k][s,r]
			else:
				v = Q[k][s,s]
			prob.linear_constraints.set_coefficients(x-1,y,v)
			prob.linear_constraints.set_coefficients(x,y,v)

	
for k in nclist:
	x = constraintrowindex
	constraintrowindex += 1
	CIndex["qxcl", k] = x
	my_rhs = [-1*clb[k]]
	prob.linear_constraints.add(rhs=my_rhs)
	prob.linear_constraints.set_senses(x, "L")
	x = constraintrowindex
	constraintrowindex += 1
	CIndex["qxcu", k] = x
	my_rhs = [-1*cub[k]]
	prob.linear_constraints.add(rhs=my_rhs)
	prob.linear_constraints.set_senses(x, "G")
	for r in range(n):
		y = numuptri + r
		v = q[k][r,0]
		prob.linear_constraints.set_coefficients(x-1,y,v)
		prob.linear_constraints.set_coefficients(x,y,v)
		for s in range(r,n):
			y = UpTriDic[r,s]
			if r!=s:
				v = Q[k][r,s]+Q[k][s,r]
			else:
				v = Q[k][s,s]
			prob.linear_constraints.set_coefficients(x-1,y,v)
			prob.linear_constraints.set_coefficients(x,y,v)


### Loop Parameters
eps = 10.0**(-4.0)
eps2 = eps/10.0


eps3 = 0.01 ## Incremental change in C bounds
brad = bsteps[0]
newb = brad*ones(m)
if brad <= eps:
	eps = brad/10.0
	eps2 = eps/10.0
	
maxcub = cub.copy()
minclb = clb.copy()
testcub = cub.copy()
testclb = clb.copy()
NonConvergentRuns = 0

#### Reset constraints involving newb and testclb/cub
## Ax<=b
for d in range(m):
	prob.linear_constraints.set_rhs(CIndex["axb",d],newb[d])
				
## -Axb^T-b(Ax)^T+AXA^T >= -bb
for L in range(m):
	for K in range(m):
		x = CIndex["axa",L,K]
		my_rhs = -1*newb[L]*newb[K]
		prob.linear_constraints.set_rhs(x,my_rhs)
		for r in range(n):
			y = numuptri + r
			v = -(A[L,r]*newb[K]+newb[L]*A[K,r])
			prob.linear_constraints.set_coefficients(x,y,v)

start = time.clock()



while NonConvergentRuns <= 2: 
	TestStatus = 1

	for d in range(m):
		for i in range(n):
			prob.objective.set_linear(numuptri+i,A[d,i])

		## Constraint  A[i,:]x-b_i=0
		x = CIndex["axb",d]
		prob.linear_constraints.set_senses(x, "E")
		prob.solve()
		status = prob.solution.get_status()
		prob.linear_constraints.set_senses(x, "L")

		if status != 3:
			TestStatus = 0
			break

	if TestStatus == 1:
		maxcub = testcub.copy()
		minclb = testclb.copy()
		orig_stdout = sys.stdout
		f = file(logfile,'a')
		sys.stdout = f
		print "Maxcub ", maxcub
		sys.stdout = orig_stdout
		f.close()

		for k in clist:
			testclb[k] -= eps3
			testcub[k] += eps3

		#### Reset constraints involving newb and testclb/cub
		## Tr(QX) + q^tx <=/>= -clb/-cub
		for k in clist:
			x = CIndex["qxcl", k]
			my_rhs = -1*testclb[k]
			prob.linear_constraints.set_rhs(x,my_rhs)

			x = CIndex["qxcu", k]
			my_rhs = -1*testcub[k]
			prob.linear_constraints.set_rhs(x,my_rhs)

	else:
		NonConvergentRuns += 1

		for k in clist:
			testclb[k] += eps3
			testcub[k] -= eps3

		eps3 = eps3/10.0
		for k in clist:
			testclb[k] -= eps3
			testcub[k] += eps3

		## Tr(QX) + q^tx <=/>= -clb/-cub
		for k in clist:
			x = CIndex["qxcl", k]
			my_rhs = -1*testclb[k]
			prob.linear_constraints.set_rhs(x,my_rhs)

			x = CIndex["qxcu", k]
			my_rhs = -1*testcub[k]
			prob.linear_constraints.set_rhs(x,my_rhs)

## End Find Max C Rad, Print to File
etime = time.clock()-start
icrad = maxcub[clist[0]]
print "max c rad is ", icrad
time.sleep(1)
orig_stdout = sys.stdout
f = file(outfile,'a')
sys.stdout = f
print brad, ",", icrad, ",", etime
sys.stdout = orig_stdout
f.close()























