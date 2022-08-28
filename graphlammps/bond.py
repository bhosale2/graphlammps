#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Jun  5 15:51:56 2022

@author: ckondur
"""

import numpy as np
import sys
import subprocess
import os


class bond_info:
    def __init__(self):
        self.id = 1
        self.type = 1
        self.nb = 1
        self.id_nb = []
        self.mol = 0
        self.bo_nb = []
        self.abo = 0
        self.nlp = 0
        self.q = 0
        self.type_nb = []


use_cache = True  # Use cache or not?
warn_cache = True  # Print the cache warnings or not?


class bonds:
    def __init__(self, fname, dt=0.1e-3):
        self.fname = os.path.abspath(fname)
        self.dt = dt

        self.use_cache = use_cache  # Use cache or not?
        self.warn_cache = warn_cache  # Print the cache warnings or not?

        try:
            self.fr = open(self.fname, "r")
        except:
            sys.exit(f"Unable to open file {self.fname}. \nExiting.")

        # Create the position of file pointers necessary to jump around
        self.line_offset = []
        offset = 0

        if self.use_cache:
            cache_bonds_fname = self.fname + ".cache"
            cache_exist = os.path.isfile(cache_bonds_fname)

            if not cache_exist:
                write_cache = True
                if self.warn_cache:
                    print("Bonds cache does not exist. Will write new cache.")
            else:
                write_cache = False
                fc = open(cache_bonds_fname, "r+")
                file_fname = fc.readline()
                file_mtime = fc.readline()
                mtime = "%s" % (os.path.getmtime(self.fname))
                if (
                    file_fname.strip() != self.fname.strip()
                    or file_mtime.strip() != mtime.strip()
                ):
                    write_cache = True
                    if self.warn_cache:
                        print(
                            "Bonds cache exists, but is outdated. Will write new cache."
                        )
                    # print(file_fname.strip(),self.fname.strip())
                    # print(file_mtime.strip(),mtime.strip())
                else:
                    if self.warn_cache:
                        print(
                            "Bonds cache exists and is up to date. Will read the cache."
                        )
                    self.num_timesteps = int(fc.readline())
                    for i in range(self.num_timesteps):
                        line = fc.readline().split()
                        self.line_offset.append(
                            [int(line[0]), int(line[1]), int(line[2])]
                        )
                fc.close()

        if (self.use_cache == False) or (self.use_cache and write_cache):
            with open(self.fname) as fr:
                for line in fr:
                    offset_beg = offset
                    if "Timestep" in line.split():
                        ts = int(line.split()[-1])
                        offset += len(line)

                        for i in range(6):
                            line = fr.readline()
                            offset += len(line)
                        natoms = 0
                        while True:
                            line = fr.readline()
                            offset += len(line)
                            if "#" in line.split():
                                break
                            else:
                                natoms += 1
                        self.line_offset.append([ts, offset_beg, natoms])
                    else:
                        sys.exit(
                            f" Error while mapping the bonds file : {self.fname}\n Timestep not found at the expected location in the bonds file. !!!!!\n Check near timestep {ts}\n {line}"
                        )

        if self.use_cache and write_cache:
            if self.warn_cache:
                print("Writing cache for the bonds file.")
            fc = open(cache_bonds_fname, "w")
            fc.write("%s\n" % (self.fname))
            mtime = os.path.getmtime(self.fname)
            fc.write("%s\n" % (mtime))
            fc.write("%d\n" % (len(self.line_offset)))
            for i in range(len(self.line_offset)):
                fc.write(
                    "%d %d %d\n"
                    % (
                        self.line_offset[i][0],
                        self.line_offset[i][1],
                        self.line_offset[i][2],
                    )
                )
            fc.close()

        self.fr.seek(0)
        self.line_offset = np.array(self.line_offset)
        self.num_timesteps = len(self.line_offset)

    def read_bonds_timestep(self, step):

        # Check if the step is valid
        idx = np.where(self.line_offset[:, 0] == step)[0]

        if len(idx) == 0:
            sys.exit(f"Time step {step} not found in bonds file.")
        else:
            idx = idx[0]
            self.num_atoms = self.line_offset[idx][2]

        # Get the file pointer to move to the appropriate location
        self.fr.seek(self.line_offset[idx][1])

        # Read the bonds information
        self.__read_bonds_info()

    def __read_bonds_info(self):
        """This function assumes the file pointer is at the begining of a timestep and reads the bonds information"""
        line = self.fr.readline()
        # print(line)
        if len(line) == 0:
            # self.fr.close()
            raise Exception(f" Reached end of file : {self.fname}")
        else:
            self.timestep = int(line.split()[-1])
            self.time = self.timestep * self.dt

            line = self.fr.readline()
            line = self.fr.readline().split()

            # self.num_atoms = int(line[-1])

            for _ in range(4):
                line = self.fr.readline()

            self.bonds_list = []

            for i in range(self.num_atoms):
                bond = bond_info()
                line = self.fr.readline().split()
                bond.id = int(line[0])
                bond.type = int(line[1])
                bond.nb = int(line[2])
                bond.id_nb = np.zeros((bond.nb,), dtype=int)
                # print(bond.id_nb)
                for j in range(bond.nb):
                    bond.id_nb[j] = int(line[j + 3])
                bond.mol = int(line[3 + bond.nb])
                bond.bo_nb = np.zeros((bond.nb,), dtype=float)
                for j in range(bond.nb):
                    bond.bo_nb[j] = float(line[j + 4 + bond.nb])

                bond.abo = float(line[-3])
                bond.nlp = float(line[-2])
                bond.q = float(line[-1])

                self.bonds_list.append(bond)

            line = self.fr.readline()

            # Sort the bonds list based on the id attribute
            self.bonds_list.sort(key=lambda x: x.id)

    def read_next_timestep(self):
        ts_curr = self.timestep
        idx = np.where(ts_curr == self.line_offset[:, 0])[0][0]
        ts_curr = self.line_offset[idx + 1][0]
        self.read_bonds_timestep(ts_curr)

    def close(self):
        self.fr.close()

    def get_O2_atoms_id(self, O_type=3):
        num_atoms = len(self.bonds_list)
        O_atoms = []
        O2_idx = []

        ## Create a list of atoms with exactly one neighbor
        for i in range(num_atoms):
            b = self.bonds_list[i]
            if b.type == O_type and b.nb == 1:
                O_atoms.append(i)

        # Go through the list and find the O atoms comprising the molecule
        for i in range(len(O_atoms)):
            Oa = self.bonds_list[int(O_atoms[i])]
            for j in range(i + 1, len(O_atoms)):
                Ob = self.bonds_list[int(O_atoms[j])]
                if Oa.id in Ob.id_nb:
                    temp = [Oa.id, Ob.id]
                    O2_idx.append([min(temp), max(temp)])
                    break

        # print("%d O2 molecules found at timestep %d"%(len(O2_idx), self.timestep))
        return O2_idx

    def get_neighbor_info(self, idx):
        """Update the idenities of the neighboring atoms"""
        self.bonds_list[idx].type_nb = []
        for i in self.bonds_list[idx].id_nb:
            j = self.get_bond(i)
            self.bonds_list[idx].type_nb.append(self.bonds_list[j].type)

    def get_bond(self, idx):
        """In some cases the bonds_list[idx].id will not equal idx+1
        In those cases, use this function to get i where bonds_list[i] == idx"""
        for i in range(len(self.bonds_list)):
            if self.bonds_list[i].id == idx:
                return i
        sys.exit("Error in get_bond(): No bond with id==idx found.")
