# -*- coding: utf-8 -*-
"""
Created on Mon Jul 20 15:53:14 2015

@author: uwe
"""

from functools import partial
from warnings import warn
import logging
import os

import dill as pickle

from oemof.core.network import Entity
from oemof.core.network.entities.components import transports as transport
from oemof.groupings import (DEFAULT as BY_UID, Grouping as GroupingBase,
                             Nodes as Grouping)
from oemof.network import Node


def MultipleGroups(*args):
    warn("`MultipleGroups` is DEPRECATED.\n" +
         "Just return a list of group keys instead.",
         DeprecationWarning)
    return list(args)


class EnergySystem:
    r"""Defining an energy supply system to use oemof's solver libraries.

    Note
    ----
    The list of regions is not necessary to use the energy system with solph.

    Parameters
    ----------
    entities : list of :class:`Entity <oemof.core.network.Entity>`, optional
        A list containing the already existing :class:`Entities
        <oemof.core.network.Entity>` that should be part of the energy system.
        Stored in the :attr:`entities` attribute.
        Defaults to `[]` if not supplied.
    simulation : core.energy_system.Simulation object
        Simulation object that contains all necessary attributes to start the
        solver library. Defined in the :py:class:`Simulation
        <oemof.core.energy_system.Simulation>` class.
    regions : list of core.energy_system.Region objects
        List of regions defined in the :py:class:`Region
        <oemof.core.energy_system.Simulation>` class.
    time_idx : pandas.index, optional
        Define the time range and increment for the energy system. This is an
        optional parameter but might be import for other functions/methods that
        use the EnergySystem class as an input parameter.
    groupings : list
        The elements of this list are used to construct :class:`Groupings
        <oemof.core.energy_system.Grouping>` or they are used directly if they
        are instances of :class:`Grouping <oemof.core.energy_system.Grouping>`.
        These groupings are then used to aggregate the entities added to this
        energy system into :attr:`groups`.
        By default, there'll always be one group for each :attr:`uid
        <oemof.core.network.Entity.uid>` containing exactly the entity with the
        given :attr:`uid <oemof.core.network.Entity.uid>`.
        See the :ref:`examples <energy-system-examples>` for more information.

    Attributes
    ----------
    entities : list of :class:`Entity <oemof.core.network.Entity>`
        A list containing the :class:`Entities <oemof.core.network.Entity>`
        that comprise the energy system. If this :class:`EnergySystem` is
        set as the :attr:`registry <oemof.core.network.Entity.registry>`
        attribute, which is done automatically on :class:`EnergySystem`
        construction, newly created :class:`Entities
        <oemof.core.network.Entity>` are automatically added to this list on
        construction.
    groups : dict
    simulation : core.energy_system.Simulation object
        Simulation object that contains all necessary attributes to start the
        solver library. Defined in the :py:class:`Simulation
        <oemof.core.energy_system.Simulation>` class.
    regions : list of core.energy_system.Region objects
        List of regions defined in the :py:class:`Region
        <oemof.core.energy_system.Simulation>` class.
    results : dictionary
        A dictionary holding the results produced by the energy system.
        Is `None` while no results are produced.
        Currently only set after a call to :meth:`optimize` after which it
        holds the return value of :meth:`om.results()
        <oemof.solph.optimization_model.OptimizationModel.results>`.
        See the documentation of that method for a detailed description of the
        structure of the results dictionary.
    time_idx : pandas.index, optional
        Define the time range and increment for the energy system. This is an
        optional atribute but might be import for other functions/methods that
        use the EnergySystem class as an input parameter.


    .. _energy-system-examples:
    Examples
    --------

    Regardles of additional groupings, :class:`entities
    <oemof.core.network.Entity>` will always be grouped by their :attr:`uid
    <oemof.core.network.Entity.uid>`:

    >>> from oemof.core.network import Entity
    >>> from oemof.core.network.entities import Bus, Component
    >>> es = EnergySystem()
    >>> bus = Bus(uid='electricity')
    >>> bus is es.groups['electricity']
    True

    For simple user defined groupings, you can just supply a function that
    computes a key from an :class:`entity <oemof.core.network.Entity>` and the
    resulting groups will be sets of :class:`entities
    <oemof.core.network.Entity>` stored under the returned keys, like in this
    example, where :class:`entities <oemof.core.network.Entity>` are grouped by
    their `type`:

    >>> es = EnergySystem(groupings=[type])
    >>> buses = set(Bus(uid="Bus {}".format(i)) for i in range(9))
    >>> components = set( Component(uid="Component {}".format(i))
    ...                   for i in range(9))
    >>> buses == es.groups[Bus]
    True
    >>> components == es.groups[Component]
    True

    """
    def __init__(self, **kwargs):
        for attribute in ['regions', 'entities', 'simulation']:
            setattr(self, attribute, kwargs.get(attribute, []))

        Entity.registry = self
        Node.registry = self
        self._groups = {}
        self._groupings = ( [BY_UID] +
                            [ g if isinstance(g, GroupingBase) else Grouping(g)
                              for g in kwargs.get('groupings', [])])
        for e in self.entities:
            for g in self._groupings:
                g(e, self.groups)
        self.results = kwargs.get('results')
        self.time_idx = kwargs.get('time_idx')

    @staticmethod
    def _regroup(entity, groups, groupings):
        for g in groupings:
            g(entity, groups)
        return groups

    def add(self, entity):
        """ Add an `entity` to this energy system.
        """
        self.entities.append(entity)
        self._groups = partial(self._regroup, entity, self.groups,
                               self._groupings)

    @property
    def groups(self):
        while callable(self._groups):
            self._groups = self._groups()
        return self._groups

    @property
    def nodes(self):
        return self.entities

    @nodes.setter
    def nodes(self, value):
        self.entities = value

    def dump(self, dpath=None, filename=None, keep_weather=True):
        r""" Dump an EnergySystem instance.
        """
        if dpath is None:
            bpath = os.path.join(os.path.expanduser("~"), '.oemof')
            if not os.path.isdir(bpath):
                os.mkdir(bpath)
            dpath = os.path.join(bpath, 'dumps')
            if not os.path.isdir(dpath):
                os.mkdir(dpath)

        if filename is None:
            filename = 'es_dump.oemof'

        pickle.dump(self.__dict__, open(os.path.join(dpath, filename), 'wb'))

        msg = ('Attributes dumped to: {0}'.format(os.path.join(
            dpath, filename)))
        logging.debug(msg)
        return msg

    def restore(self, dpath=None, filename=None):
        r""" Restore an EnergySystem instance.
        """
        logging.info(
            "Restoring attributes will overwrite existing attributes.")
        if dpath is None:
            dpath = os.path.join(os.path.expanduser("~"), '.oemof', 'dumps')

        if filename is None:
            filename = 'es_dump.oemof'

        self.__dict__ = pickle.load(open(os.path.join(dpath, filename), "rb"))
        msg = ('Attributes restored from: {0}'.format(os.path.join(
            dpath, filename)))
        logging.debug(msg)
        return msg


class Region:
    r"""Defining a region within an energy supply system.

    Note
    ----
    The list of regions is not necessary to use the energy system with solph.

    Parameters
    ----------
    entities : list of core.network objects
        List of all objects of the energy system. All class descriptions can
        be found in the :py:mod:`oemof.core.network` package.
    name : string
        A unique name to identify the region. If possible use typical names for
        regions and english names for countries.
    code : string
        A short unique name to identify the region.
    geom : shapely.geometry object
        The geometry representing the region must be a polygon or a multi
        polygon.

    Attributes
    ----------
    entities : list of core.network objects
        List of all objects of the energy system. All class descriptions can
        be found in the :py:mod:`oemof.core.network` package.
    name : string
        A unique name to identify the region. If possible use typical names for
        regions and english names for countries.
    geom : shapely.geometry object
        The geometry representing the region must be a polygon or a multi
        polygon.
    """
    def __init__(self, **kwargs):
        self.entities = []  # list of entities
        self.add_entities(kwargs.get('entities', []))

        self.name = kwargs.get('name')
        self.geom = kwargs.get('geom')
        self._code = kwargs.get('code')

    # TODO: oder sollte das ein setter sein? Yupp.
    def add_entities(self, entities):
        """Add a list of entities to the existing list of entities.

        For every entity added to a region the region attribute of the entity
        is set

        Parameters
        ----------
        entities : list of core.network objects
            List of all objects of the energy system that belongs to area
            covered by the polygon of the region. All class descriptions can
            be found in the :py:mod:`oemof.core.network` package.
        """

        # TODO: prevent duplicate entries
        self.entities.extend(entities)
        for entity in entities:
            if self not in entity.regions:
                entity.regions.append(self)

    @property
    def code(self):
        """Creating a short code based on the region name if no code is set."""
        if self._code is None:
            name_parts = self.name.replace('_', ' ').split(' ', 1)
            self._code = ''
            for part in name_parts:
                self._code += part[:1].upper() + part[1:3]
        return self._code


class Simulation:
    r"""Defining the simulation related parameters according to the solver lib.

    Parameters
    ----------
    solver : string
        Name of the solver supported by the used solver library.
        (e.g. 'glpk', 'gurobi')
    debug : boolean
        Set the chosen solver to debug (verbose) mode to get more information.
    verbose : boolean
        If True, solver output etc. is streamed in python console
    duals : boolean
        If True, results of dual variables and reduced costs will be saved
    objective_options : dictionary
        'function': function to use from
                    :py:mod:`oemof.solph.predefined_objectives`
        'cost_objects': list of str(`class`) elements. Objects of type  `class`
                        are include in cost terms of objective function.
        'revenue_objects': list of str(`class`) elements. . Objects of type
                           `class` are include in revenue terms of
                           objective function.
    timesteps : list or sequence object
         Timesteps to be simulated or optimized in the used library
    relaxed : boolean
        If True, integer variables will be relaxed
        (only relevant for milp-problems)
    fast_build : boolean
        If True, the standard way of pyomo constraint building is skipped and
        a different function is used.
        (Warning: No guarantee that all expected 'standard' pyomo model
        functionalities work for the constructed model!)
    """
    def __init__(self, **kwargs):
        ''
        self.solver = kwargs.get('solver', 'glpk')
        self.debug = kwargs.get('debug', False)
        self.verbose = kwargs.get('verbose', False)
        self.objective_options = kwargs.get('objective_options', {})
        self.duals = kwargs.get('duals', False)
        self.timesteps = kwargs.get('timesteps')
        self.relaxed = kwargs.get('relaxed', False)
        self.fast_build = kwargs.get('fast_build', False)
        self.solve_kwargs = kwargs.get('solve_kwargs', {})

        if self.timesteps is None:
            raise ValueError('No timesteps defined!')
