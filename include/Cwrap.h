/*
Title: P3DFFT++ library

Authors: Dmitry Pekurovsky

Copyright (c) 2006-2019 

The Regents of the University of California.

All Rights Reserved.                        

 

    Permission to use, copy, modify and  distribute  any part

    of this software for  educational,  research  and  non-profit

    purposes, by individuals or non-profit organizations,

    without fee,  and  without a written  agreement is

    hereby granted,  provided  that the  above  copyright notice,

    this paragraph  and the following  three  paragraphs appear in

    all copies.       

 

    For-profit organizations desiring to use this software and others

    wishing to incorporate this  software into commercial

    products or use it for  commercial  purposes should contact the:    

          Office of Innovation & Commercialization 

          University of California San Diego

          9500 Gilman Drive,  La Jolla,  California, 92093-0910        

          Phone: (858) 534-5815

          E-mail: innovation@ucsd.edu

 

    IN NO EVENT SHALL THE UNIVERSITY OF CALIFORNIA BE LIABLE

    TO ANY PARTY FOR DIRECT, INDIRECT, SPECIAL, INCIDENTAL, OR    

    CONSEQUENTIAL DAMAGES, INCLUDING LOST PROFITS, ARISING OUT

    OF THE USE OF THIS SOFTWARE, EVEN IF THE UNIVERSITY OF

    CALIFORNIA HAS BEEN ADVISED OF THE POSSIBILITY OF SUCH

    DAMAGE.

 

    THE SOFTWARE PROVIDED HEREUNDER IS ON AN "AS IS" BASIS, AND

    THE UNIVERSITY OF CALIFORNIA HAS NO OBLIGATIONS TO PROVIDE        

    MAINTENANCE, SUPPORT, UPDATES, ENHANCEMENTS, OR MODIFICATIONS. 

    THE UNIVERSITY OF CALIFORNIA MAKES NO REPRESENTATIONS AND    

    EXTENDS NO WARRANTIES OF ANY KIND, EITHER EXPRESSED OR

    IMPLIED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES

    OF MERCHANTABILITY OR FITNESS FOR A PARTICULAR PURPOSE, OR

    THAT THE USE OF THE MATERIAL WILL NOT INFRINGE ANY PATENT,        

    TRADEMARK OR OTHER RIGHTS.
*/

struct Grid_struct {
  int taskid,numtasks;
  int nd;  //number of dimensions the volume is split over
  int gdims[3];  //Global dimensions
  int dim_conj_sym; // Dimension of conjugate symmetry, where we store N/2+1 of the data after R2C transform due to conjugate symmety; =-1 if none
  int mem_order[3];  //Memory ordering inside the data volume
  int ldims[3];  //Local dimensions on THIS processor
  int pgrid[3];  //Processor grid
  int proc_order[3];   //Ordering of tasks in processor grid, e.g. (1,2,3) : first dimension - adjacent tasks,then second, then third dimension
  int P[3];  //Processor grid size (in inverse order of split dimensions, i.e. rows first, then columns etc
  int D[3];  //Ranks of Dimensions of physical grid split over rows and columns correspondingly
  int L[3];  //Rank of Local dimension (p=1)
  int grid_id[3];  //Position of this pencil/cube in the processor grid
  int grid_id_cart[3];
  int glob_start[3]; // Starting coords of this cube in the global grid
  MPI_Comm mpi_comm_glob; // Global MPi communicator we are starting from
  MPI_Comm mpi_comm_cart;
  MPI_Comm mpicomm[3]; //MPI communicators for each dimension 
} ;

typedef struct Grid_struct Grid;

void p3dfft_setup();
void p3dfft_cleanup();
  Type3D p3dfft_init_3Dtype(int[3]); //,char *);
  int p3dfft_plan_1Dtrans(Grid *,Grid *,int,int);
Plan3D p3dfft_plan_3Dtrans(Grid *,Grid *,Type3D);
  int find_grid(int [3],int [3],int [3],int [3],MPI_Comm);
Grid *p3dfft_init_grid(int[3],int,int[3],int[3],int[3],MPI_Comm);
  //void p3dfft_free_grid_f(int *gr);
void p3dfft_free_grid(Grid *gr);
void p3dfft_inv_mo(int [3],int [3]);
void p3dfft_write_buf(double *,char *,int [3],int [3]);
void p3dfft_exec_1Dtrans_double(int,double *,double *, int);
void p3dfft_exec_1Dtrans_single(int,float *,float *, int);
void p3dfft_exec_3Dtrans_double(Plan3D,double *,double *, int);
void p3dfft_exec_3Dtrans_single(Plan3D,float *,float *, int);
void p3dfft_exec_3Dderiv_double(Plan3D,double *,double *,int, int);
void p3dfft_exec_3Dderiv_single(Plan3D,float *,float *,int, int);
void p3dfft_compute_deriv_single(float *,float *,Grid *,int);
void p3dfft_compute_deriv_double(double *,double *,Grid *,int);
