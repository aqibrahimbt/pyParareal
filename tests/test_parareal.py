import sys
sys.path.append('../src')

from parareal import parareal
from timemesh import timemesh
from impeuler import impeuler
from solution_linear import solution_linear
import unittest
import numpy as np
from scipy import sparse
from scipy.sparse import linalg

class TestParareal(unittest.TestCase):

  def setUp(self):
    times        = np.sort( np.random.rand(2) )
    self.tstart  = times[0]
    self.tend    = times[1]
    self.nslices = np.random.randint(2,32) 
    steps        = np.sort( np.random.randint(low=1, high=64, size=2) )
    self.ncoarse = steps[0]
    self.nfine   = steps[1]
    self.ndof    = np.random.randint(1,16)
    #self.ndof    = 2
    #self.nslices = 3
    self.A       = sparse.spdiags([ np.ones(self.ndof), -2.0*np.ones(self.ndof), np.ones(self.ndof)], [-1,0,1], self.ndof, self.ndof, format="csc")
    self.M       = sparse.spdiags([ 10.0+np.random.rand(self.ndof) ], [0], self.ndof, self.ndof, format="csc")
    self.u0      = solution_linear(np.ones((self.ndof,1)), self.A, self.M)

  # Can instantiate object of type parareal
  def test_caninstantiate(self):
    para = parareal(self.tstart, self.tend, self.nslices, impeuler, impeuler, self.nfine, self.ncoarse, 1e-10, 5, self.u0)

  # Can execute run function
  def test_canrun(self):
    para = parareal(self.tstart, self.tend, self.nslices, impeuler, impeuler, self.nfine, self.ncoarse, 1e-10, 5, self.u0)
    para.run()  

  # Test matrix Parareal
  def test_pararealmatrix(self):
    para = parareal(self.tstart, self.tend, self.nslices, impeuler, impeuler, self.nfine, self.ncoarse, 1e-10, 1, self.u0)
    Pmat, Bmat = para.get_parareal_matrix()
    bvec = np.zeros((self.ndof*(self.nslices+1),1))
    bvec[0:self.ndof,:] = self.u0.y
    # Perform one coarse step by matrix multiplication
    y0 = Bmat.dot(bvec)
    # Perform one Parareal step in matrix form
    y_mat = Pmat.dot(y0) + Bmat.dot(bvec)
    para.run()
    y_para = np.zeros((self.ndof*(self.nslices+1),1))
    y_para[0:self.ndof,:] = self.u0.y
    for i in range(0,self.nslices):
      y_para[(i+1)*self.ndof:(i+2)*self.ndof,:] = para.get_end_value(i).y
    err = np.linalg.norm(y_para - y_mat, np.inf)
    assert err<1e-12, ("Parareal run and matrix form do not yield identical results for a single iteration. Error: %5.3e" % err)

  # Test matrix Parareal
  def test_pararealmatrixmultiple(self):
    niter = np.random.randint(2,8) 
    para = parareal(self.tstart, self.tend, self.nslices, impeuler, impeuler, self.nfine, self.ncoarse, 0.0, niter, self.u0)
    Pmat, Bmat = para.get_parareal_matrix()
    bvec = np.zeros((self.ndof*(self.nslices+1),1))
    bvec[0:self.ndof,:] = self.u0.y
    # Perform one coarse step by matrix multiplication
    y_mat = Bmat.dot(bvec)
    # Perform niter Parareal step in matrix form
    for i in range(0,niter):
      y_mat = Pmat.dot(y_mat) + Bmat.dot(bvec)
    para.run()
    y_para = np.zeros((self.ndof*(self.nslices+1),1))
    y_para[0:self.ndof,:] = self.u0.y
    for i in range(0,self.nslices):
      y_para[(i+1)*self.ndof:(i+2)*self.ndof,:] = para.get_end_value(i).y
    err = np.linalg.norm(y_para - y_mat, np.inf)
    assert err<1e-12, ("Parareal run and matrix form do not yield identical results for multiple iterations. Error: %5.3e" % err)

  # Parareal reproduces fine solution after niter=nslice many iterations
  def test_reproducesfine(self):
    # Smaller number of slices to keep runtime short
    nslices = np.random.randint(2,12) 
    para = parareal(self.tstart, self.tend, nslices, impeuler, impeuler, self.nfine, self.ncoarse, 0.0, nslices, self.u0)
    Fmat = para.timemesh.get_fine_matrix(self.u0)
    b = np.zeros((self.ndof*(nslices+1),1))
    b[0:self.ndof,:] = self.u0.y
    # Solve system
    u = linalg.spsolve(Fmat, b)
    u = u.reshape((self.ndof*(nslices+1),1))
    # Run Parareal
    para.run()
    u_para = para.get_parareal_vector()
    diff = np.linalg.norm(u_para - u, np.inf)
    assert diff<1e-12, ("Parareal does not reproduce fine solution after nslice=niter many iterations. Error: %5.3e" % diff)

  # Fine solution is fixed point of Parareal iteration
  def test_fineisfixedpoint(self):
    niter = np.random.randint(2,8) 
    para = parareal(self.tstart, self.tend, self.nslices, impeuler, impeuler, self.nfine, self.ncoarse, 0.0, niter, self.u0)
    Fmat = para.timemesh.get_fine_matrix(self.u0)
    b = np.zeros((self.ndof*(self.nslices+1),1))
    b[0:self.ndof,:] = self.u0.y
    # Solve system
    u = linalg.spsolve(Fmat, b)
    u = u.reshape((self.ndof*(self.nslices+1),1))
    # Get Parareal iteration matrices
    Pmat, Bmat = para.get_parareal_matrix()
    # Apply matrix to fine solution
    u_para = Pmat.dot(u) + Bmat.dot(b)
    diff = np.linalg.norm( u_para - u, np.inf)
    assert diff<1e-14, ("Fine solution is not a fixed point of Parareal iteration - difference %5.3e" % diff)

  # Stability function is equivalent to full run of Parareal
  def test_stabfunction(self):
    niter = np.random.randint(2,8)
    para  = parareal(self.tstart, self.tend, self.nslices, impeuler, impeuler, self.nfine, self.ncoarse, 0.0, niter, self.u0)
    Smat  = para.get_parareal_stab_function(niter)
    y_mat =  Smat.dot(self.u0.y)
    para.run()
    y_par = para.get_last_end_value().y
    diff  = np.linalg.norm(y_mat - y_par, np.inf)
    assert diff<1e-12, ("Generated Parareal stability matrix does not match result from run(). Error: %5.3e" % diff)
