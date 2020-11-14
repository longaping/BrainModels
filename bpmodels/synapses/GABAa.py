# -*- coding: utf-8 -*-

import brainpy as bp
import brainpy.numpy as np

def get_GABAa1(g_max=0.4, E=-80., tau_decay=6.):
    """
    GABAa conductance-based synapse model (differential form).

    .. math::
        
        I_{syn}&= - \\bar{g}_{max} s (V - E)

        \\frac{d s}{d t}&=-\\frac{s}{\\tau_{decay}}+\\sum_{k}\\delta(t-t-{j}^{k})

    Args:
        g_max (float): Maximum synapse conductance.
        E (float): Reversal potential of synapse.
        tau_decay (float): Time constant of gating variable decay.

    Returns:
        bp.SynType: return description of GABAa synapse model.

    """
    requires = dict(
        ST=bp.types.SynState(['s', 'g'], help = "GABAa synapse state"),
        pre=bp.types.NeuState(['spike'], help = "Pre-synaptic neuron state must have 'spike' item"),
        post=bp.types.NeuState(['V', 'input'], help = "Post-synaptic neuron state must have 'V' and 'input' item"),
        pre2syn=bp.types.ListConn(help="Pre-synaptic neuron index -> synapse index"),
        post2syn=bp.types.ListConn(help="Post-synaptic neuron index -> synapse index")
    )

    @bp.integrate
    def int_s(s, t):
        return - s / tau_decay

    def update(ST, pre, pre2syn):
        s = int_s(ST['s'], 0.)
        for pre_id in np.where(pre['spike'] > 0.)[0]:
            syn_ids = pre2syn[pre_id]
            s[syn_ids] += 1
        ST['s'] = s
        ST['g'] = g_max * s

    @bp.delayed
    def output(ST, post, post2syn):
        post_cond = np.zeros(len(post2syn), dtype=np.float_)
        for post_id, syn_ids in enumerate(post2syn):
            post_cond[post_id] = np.sum(ST['g'][syn_ids])
        post['input'] -= post_cond * (post['V'] - E)

    return bp.SynType(name='GABAa1',
                      requires=requires,
                      steps=(update, output),
                      vector_based=True)


def get_GABAa2(g_max=0.04, E=-80., alpha=0.53, beta=0.18, T=1., T_duration=1.):
    """
    GABAa conductance-based synapse model (markov form).

    .. math::
        
        I_{syn}&= - \\bar{g}_{max} s (V - E)

        \\frac{d r}{d t}&=\\alpha[T]^2(1-s) - \\beta s

    Args:
        g_max (float): Maximum synapse conductance.
        E (float): Reversal potential of synapse.
        alpha (float): Opening rate constant of ion channel.
        beta (float): Closing rate constant of ion channel.
        T (float): Transmitter concentration when synapse is triggered by a pre-synaptic spike.
        T_duration (float): Transmitter concentration duration time after being triggered.

    Returns:
        bp.SynType: return description of GABAa synapse model.

    """
    requires = dict(
        ST=bp.types.SynState({'s': 0., 'g': 0., 't_last_pre_spike': -1e7}, help = "GABAa synapse state"),
        pre=bp.types.NeuState(['spike'], help = "Pre-synaptic neuron state must have 'spike' item"), 
        post=bp.types.NeuState(['V', 'input'], help = "Post-synaptic neuron state must have 'V' and 'input' item"),
        pre2syn=bp.types.ListConn(help = "Pre-synaptic neuron index -> synapse index"),
        post2syn=bp.types.ListConn(help = "Post-synaptic neuron index -> synapse index")
    )

    @bp.integrate
    def int_s(s, t, TT):
        return alpha * TT * (1 - s) - beta * s

    def update(ST, pre, pre2syn, _t_):
        for pre_id in np.where(pre['spike'] > 0.)[0]:
            syn_ids = pre2syn[pre_id]
            ST['t_last_pre_spike'][syn_ids] = _t_
        TT = ((_t_ - ST['t_last_pre_spike']) < T_duration) * T
        s = int_s(ST['s'], _t_, TT)
        ST['s'] = s
        ST['g'] = g_max * s

    @bp.delayed
    def output(ST, post, post2syn):
        post_cond = np.zeros(len(post2syn), dtype=np.float_)
        for post_id, syn_ids in enumerate(post2syn):
            post_cond[post_id] = np.sum(ST['g'][syn_ids])
        post['input'] -= post_cond * (post['V'] - E)

    return bp.SynType(name='GABAa2',
                      requires=requires,
                      steps=(update, output),
                      vector_based=True)