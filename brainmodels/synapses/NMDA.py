# -*- coding: utf-8 -*-

import brainpy as bp
import brainpy.math as bm

__all__ = [
  'NMDA'
]


class NMDA(bp.TwoEndConn):
  r"""Conductance-based NMDA synapse model.

  **Model Descriptions**

  The NMDA receptor is a glutamate receptor and ion channel found in neurons.
  The NMDA receptor is one of three types of ionotropic glutamate receptors,
  the other two being AMPA and kainate receptors.

  The NMDA receptor mediated conductance depends on the postsynaptic voltage.
  The voltage dependence is due to the blocking of the pore of the NMDA receptor
  from the outside by a positively charged magnesium ion. The channel is
  nearly completely blocked at resting potential, but the magnesium block is
  relieved if the cell is depolarized. The fraction of channels :math:`g_{\infty}`
  that are not blocked by magnesium can be fitted to
  
  .. math::
      
      g_{\infty}(V,[{Mg}^{2+}]_{o}) = (1+{e}^{-\alpha V}
      \frac{[{Mg}^{2+}]_{o}} {\beta})^{-1} 

  Here :math:`[{Mg}^{2+}]_{o}` is the extracellular magnesium concentration,
  usually 1 mM. Thus, the channel acts as a
  "coincidence detector" and only once both of these conditions are met, the
  channel opens and it allows positively charged ions (cations) to flow through
  the cell membrane [2]_.

  If we make the approximation that the magnesium block changes
  instantaneously with voltage and is independent of the gating of the channel,
  the net NMDA receptor-mediated synaptic current is given by

  .. math::

      I_{syn} = g_{NMDA}(t) (V(t)-E) \cdot g_{\infty}

  where :math:`V(t)` is the post-synaptic neuron potential, :math:`E` is the
  reversal potential.

  Simultaneously, the kinetics of synaptic state :math:`g` is given by

  .. math::

      & g_{NMDA} (t) = g_{max} g \\
      & \frac{d g}{dt} = -\frac{g} {\tau_{decay}}+a x(1-g) \\
      & \frac{d x}{dt} = -\frac{x}{\tau_{rise}}+ \sum_{k} \delta(t-t_{j}^{k})

  where the decay time of NMDA currents is usually taken to be
  :math:`\tau_{decay}` =100 ms, :math:`a= 0.5 ms^{-1}`, and :math:`\tau_{rise}` =2 ms.

  The NMDA receptor has been thought to be very important for controlling
  synaptic plasticity and mediating learning and memory functions [3]_.


  **Model Examples**

  - `Simple illustrated example <../synapses/nmda.ipynb>`_


  **Model Parameters**

  ============= ============== =============== ================================================
  **Parameter** **Init Value** **Unit**        **Explanation**
  ------------- -------------- --------------- ------------------------------------------------
  delay         0              ms              The decay length of the pre-synaptic spikes.
  g_max         .15            µmho(µS)        The synaptic maximum conductance.
  E             0              mV              The reversal potential for the synaptic current.
  alpha         .062           \               Binding constant.
  beta          3.57           \               Unbinding constant.
  cc_Mg         1.2            mM              Concentration of Magnesium ion.
  tau_decay     100            ms              The time constant of the synaptic decay phase.
  tau_rise      2              ms              The time constant of the synaptic rise phase.
  a             .5             1/ms
  ============= ============== =============== ================================================


  **Model Variables**

  =============== ================== =========================================================
  **Member name** **Initial values** **Explanation**
  --------------- ------------------ --------------------------------------------------------- 
  g               0                  Synaptic conductance.
  x               0                  Synaptic gating variable.
  pre_spike       False              The history spiking states of the pre-synaptic neurons.
  =============== ================== =========================================================
      
  **References**
  
  .. [1] Brunel N, Wang X J. Effects of neuromodulation in a 
         cortical network model of object working memory dominated 
         by recurrent inhibition[J]. 
         Journal of computational neuroscience, 2001, 11(1): 63-85.
  .. [2] Furukawa, Hiroyasu, Satinder K. Singh, Romina Mancusso, and
         Eric Gouaux. "Subunit arrangement and function in NMDA receptors."
         Nature 438, no. 7065 (2005): 185-192.
  .. [3] Li, F. and Tsien, J.Z., 2009. Memory and the NMDA receptors. The New
         England journal of medicine, 361(3), p.302.
  .. [4] https://en.wikipedia.org/wiki/NMDA_receptor

  """

  def __init__(self, pre, post, conn, delay=0., g_max=0.15, E=0., cc_Mg=1.2,
               alpha=0.062, beta=3.57, tau_decay=100., a=0.5, tau_rise=2.,
               update_type='sparse', **kwargs):
    super(NMDA, self).__init__(pre=pre, post=post, conn=conn, **kwargs)

    # checking
    assert hasattr(pre, 'spike'), 'Pre-synaptic group must has "spike" variable.'
    assert hasattr(post, 'V'), 'Post-synaptic group must has "V" variable.'
    assert hasattr(post, 'input'), 'Post-synaptic group must has "input" variable.'

    # parameters
    self.g_max = g_max
    self.E = E
    self.alpha = alpha
    self.beta = beta
    self.cc_Mg = cc_Mg
    self.tau_decay = tau_decay
    self.tau_rise = tau_rise
    self.a = a
    self.delay = delay

    # connections
    if update_type == 'sparse':
      self.pre_ids, self.post_ids = self.conn.requires('pre_ids', 'post_ids')
      self.steps.replace('update', self.sparse_update)
      self.size = len(self.pre_ids)
      self.target_backend = 'numpy'

    elif update_type == 'dense':
      raise NotImplementedError

    else:
      raise bp.errors.UnsupportedError(f'Do not support {update_type} method.')

    # variables
    self.pre_spike = self.register_constant_delay('ps', self.pre.shape, delay)
    self.g = bm.Variable(bm.zeros(self.size, dtype=bm.float_))
    self.x = bm.Variable(bm.zeros(self.size, dtype=bm.float_))

  @bp.odeint(method='exponential_euler')
  def integral(self, g, x, t):
    dxdt = -x / self.tau_rise
    dgdt = -g / self.tau_decay + self.a * x * (1 - g)
    return dgdt, dxdt

  def sparse_update(self, _t, _dt):
    self.pre_spike.push(self.pre.spike)
    delayed_pre_spike = self.pre_spike.pull()
    self.g[:], self.x[:] = self.integral(self.g, self.x, _t, dt=_dt)
    for i in range(self.size):
      pre_id, post_id = self.pre_ids[i], self.post_ids[i]
      self.x[i] += delayed_pre_spike[pre_id]
      g_inf = 1 + self.cc_Mg / self.beta * bm.exp(-self.alpha * self.post.V[post_id])
      self.post.input[post_id] -= self.g_max * self.g[i] * (self.post.V[post_id] - self.E) / g_inf
