"""
QUA-Config supporting OPX1000 w/ LF-FEM & External Mixers
"""

from pathlib import Path
import numpy as np
from qualang_tools.units import unit
from qualang_tools.plot import interrupt_on_close
from qualang_tools.results import progress_counter, fetching_tool
from qualang_tools.loops import from_array
import plotly.io as pio

pio.renderers.default = "browser"
#######################
# AUXILIARY FUNCTIONS #
#######################
u = unit(coerce_to_integer=True)

######################
# Network parameters #
######################
qop_ip = "127.0.0.1"  # Write the OPX IP address
cluster_name = "Cluster_1"  # Write your cluster_name if version >= QOP220
qop_port = None  # Write the QOP port if version < QOP220

#############
# Save Path #
#############
# Path to save data
save_dir = Path(__file__).parent.resolve() / "Data"
save_dir.mkdir(exist_ok=True)

default_additional_files = {
    Path(__file__).name: Path(__file__).name,
    "optimal_weights.npz": "optimal_weights.npz",
}

#####################
# OPX configuration #
#####################
con = "con1"
mw_fem = 1  # This should be the index of the LF-FEM module, e.g., 1
lf_fem = 5  # This should be the index of the LF-FEM module, e.g., 1
# Set octave_config to None if no octave are present
octave_config = None

# Frequencies
sampling_rate = int(1e9)  # or, int(2e9)

NV_IF_freq = 40 * u.MHz
NV_LO_freq = 2.83 * u.GHz
NV_power = 4  # power in dBm at waveform amp = 1
# Pulses lengths
initialization_len_1 = 3000 * u.ns
meas_len_1 = 500 * u.ns
long_meas_len_1 = 5_000 * u.ns

initialization_len_2 = 3000 * u.ns
meas_len_2 = 500 * u.ns
long_meas_len_2 = 5_000 * u.ns

# Relaxation time from the metastable state to the ground state after during initialization
relaxation_time = 300 * u.ns
wait_for_initialization = 5 * relaxation_time

# MW parameters
mw_amp_NV = 0.2  # in units of volts
mw_len_NV = 100 * u.ns

x180_amp_NV = 0.1  # in units of volts
x180_len_NV = 32  # in units of ns

x90_amp_NV = x180_amp_NV / 2  # in units of volts
x90_len_NV = x180_len_NV  # in units of ns

# RF parameters
rf_frequency = 10 * u.MHz
rf_amp = 0.1
rf_length = 1000

# Readout parameters
signal_threshold_1 = -2_000  # ADC untis, to convert to volts divide by 4096 (12 bit ADC)
signal_threshold_2 = -2_000  # ADC untis, to convert to volts divide by 4096 (12 bit ADC)

# Delays
detection_delay_1 = 80 * u.ns
detection_delay_2 = 80 * u.ns
laser_delay_1 = 0 * u.ns
laser_delay_2 = 0 * u.ns
mw_delay = 0 * u.ns
rf_delay = 0 * u.ns


wait_between_runs = 100

config = {
    "version": 1,
    "controllers": {
        con: {
            "type": "opx1000",
            "fems": {
                lf_fem: {
                    "type": "LF",
                    "analog_outputs": {
                        # NV I
                        1: {
                            "offset": 0.0,
                            "delay": mw_delay,
                            # The "output_mode" can be used to tailor the max voltage and frequency bandwidth, i.e.,
                            #   "direct":    1Vpp (-0.5V to 0.5V), 750MHz bandwidth (default)
                            #   "amplified": 5Vpp (-2.5V to 2.5V), 330MHz bandwidth
                            # Note, 'offset' takes absolute values, e.g., if in amplified mode and want to output 2.0 V, then set "offset": 2.0
                            "output_mode": "direct",
                            # The "sampling_rate" can be adjusted by using more FEM cores, i.e.,
                            #   1 GS/s: uses one core per output (default)
                            #   2 GS/s: uses two cores per output
                            # NOTE: duration parameterization of arb. waveforms, sticky elements and chirping
                            #       aren't yet supported in 2 GS/s.
                            "sampling_rate": sampling_rate,
                            # At 1 GS/s, use the "upsampling_mode" to optimize output for
                            #   modulated pulses (optimized for modulated pulses):      "mw"    (default)
                            #   unmodulated pulses (optimized for clean step response): "pulse"
                            "upsampling_mode": "mw",
                        },
                        # NV Q
                        2: {
                            "offset": 0.0,
                            "delay": mw_delay,
                            "output_mode": "direct",
                            "sampling_rate": sampling_rate,
                            "upsampling_mode": "mw",
                        },
                        # RF
                        3: {
                            "offset": 0.0,
                            "delay": mw_delay,
                            "output_mode": "direct",
                            "sampling_rate": sampling_rate,
                            "upsampling_mode": "mw",
                        },
                    },
                    "digital_outputs": {
                        1: {},  # AOM/Laser
                        2: {},  # AOM/Laser
                        3: {},  # SPCM1 - indicator
                        4: {},  # SPCM2 - indicator
                    },
                    "analog_inputs": {
                        1: {"offset": 0, "sampling_rate": sampling_rate},  # SPCM1
                        2: {"offset": 0, "sampling_rate": sampling_rate},  # SPCM2
                    },
                },
                mw_fem: {
                    # The keyword "band" refers to the following frequency bands:
                    #   1: (50 MHz - 5.5 GHz)
                    #   2: (4.5 GHz - 7.5 GHz)
                    #   3: (6.5 GHz - 10.5 GHz)
                    # Note that the "coupled" ports O1 & I1, O2 & O3, O4 & O5, O6 & O7, and O8 & I2
                    # must be in the same band.
                    # MW-FEM outputs are delayed with respect to the LF-FEM outputs by 141ns for bands 1 and 3 and 161ns for band 2.
                    # The keyword "full_scale_power_dbm" is the maximum power of
                    # normalized pulse waveforms in [-1,1]. To convert to voltage,
                    #   power_mw = 10**(full_scale_power_dbm / 10)
                    #   max_voltage_amp = np.sqrt(2 * power_mw * 50 / 1000)
                    #   amp_in_volts = waveform * max_voltage_amp
                    #   ^ equivalent to OPX+ amp
                    # Its range is -11dBm to +16dBm with 3dBm steps.
                    "type": "MW",
                    "analog_outputs": {
                        1: {
                            "band": 1,
                            "full_scale_power_dbm": NV_power,
                            "upconverters": {1: {"frequency": NV_LO_freq}},
                        },  # NV
                    },
                    "digital_outputs": {},
                    "analog_inputs": {},
                },
            },
        }
    },
    "elements": {
        "NV": {
            "MWInput": {
                "port": (con, mw_fem, 1),
                "upconverter": 1,
            },
            "intermediate_frequency": NV_IF_freq,
            "operations": {
                "cw": "const_pulse",
                "x180": "x180_pulse",
                "x90": "x90_pulse",
                "-x90": "-x90_pulse",
                "-y90": "-y90_pulse",
                "y90": "y90_pulse",
                "y180": "y180_pulse",
            },
        },
        "RF": {
            "singleInput": {"port": (con, lf_fem, 3)},
            "intermediate_frequency": rf_frequency,
            "operations": {
                "const": "const_pulse_single",
            },
        },
        "AOM1": {
            "digitalInputs": {
                "marker": {
                    "port": (con, lf_fem, 1),
                    "delay": laser_delay_1,
                    "buffer": 0,
                },
            },
            "operations": {
                "laser_ON": "laser_ON_1",
            },
        },
        "AOM2": {
            "digitalInputs": {
                "marker": {
                    "port": (con, lf_fem, 2),
                    "delay": laser_delay_2,
                    "buffer": 0,
                },
            },
            "operations": {
                "laser_ON": "laser_ON_2",
            },
        },
        "SPCM1": {
            "singleInput": {"port": (con, lf_fem, 1)},  # not used
            "digitalInputs": {  # for visualization in simulation
                "marker": {
                    "port": (con, lf_fem, 3),
                    "delay": detection_delay_1,
                    "buffer": 0,
                },
            },
            "operations": {
                "readout": "readout_pulse_1",
                "long_readout": "long_readout_pulse_1",
            },
            "outputs": {"out1": (con, lf_fem, 1)},
            "outputPulseParameters": {
                "signalThreshold": signal_threshold_1,  # ADC units
                "signalPolarity": "Below",
                "derivativeThreshold": -2_000,
                "derivativePolarity": "Above",
            },
            "time_of_flight": detection_delay_1,
            "smearing": 0,
        },
        "SPCM2": {
            "singleInput": {"port": (con, lf_fem, 1)},  # not used
            "digitalInputs": {  # for visualization in simulation
                "marker": {
                    "port": (con, lf_fem, 4),
                    "delay": detection_delay_2,
                    "buffer": 0,
                },
            },
            "operations": {
                "readout": "readout_pulse_2",
                "long_readout": "long_readout_pulse_2",
            },
            "outputs": {"out1": (con, lf_fem, 2)},
            "outputPulseParameters": {
                "signalThreshold": signal_threshold_2,  # ADC units
                "signalPolarity": "Below",
                "derivativeThreshold": -2_000,
                "derivativePolarity": "Above",
            },
            "time_of_flight": detection_delay_2,
            "smearing": 0,
        },
    },
    "pulses": {
        "const_pulse": {
            "operation": "control",
            "length": mw_len_NV,
            "waveforms": {"I": "cw_wf", "Q": "zero_wf"},
        },
        "x180_pulse": {
            "operation": "control",
            "length": x180_len_NV,
            "waveforms": {"I": "x180_wf", "Q": "zero_wf"},
        },
        "x90_pulse": {
            "operation": "control",
            "length": x90_len_NV,
            "waveforms": {"I": "x90_wf", "Q": "zero_wf"},
        },
        "-x90_pulse": {
            "operation": "control",
            "length": x90_len_NV,
            "waveforms": {"I": "minus_x90_wf", "Q": "zero_wf"},
        },
        "-y90_pulse": {
            "operation": "control",
            "length": x90_len_NV,
            "waveforms": {"I": "zero_wf", "Q": "minus_x90_wf"},
        },
        "y90_pulse": {
            "operation": "control",
            "length": x90_len_NV,
            "waveforms": {"I": "zero_wf", "Q": "x90_wf"},
        },
        "y180_pulse": {
            "operation": "control",
            "length": x180_len_NV,
            "waveforms": {"I": "zero_wf", "Q": "x180_wf"},
        },
        "const_pulse_single": {
            "operation": "control",
            "length": rf_length,  # in ns
            "waveforms": {"single": "rf_const_wf"},
        },
        "laser_ON_1": {
            "operation": "control",
            "length": initialization_len_1,
            "digital_marker": "ON",
        },
        "laser_ON_2": {
            "operation": "control",
            "length": initialization_len_2,
            "digital_marker": "ON",
        },
        "readout_pulse_1": {
            "operation": "measurement",
            "length": meas_len_1,
            "digital_marker": "ON",
            "waveforms": {"single": "zero_wf"},
        },
        "long_readout_pulse_1": {
            "operation": "measurement",
            "length": long_meas_len_1,
            "digital_marker": "ON",
            "waveforms": {"single": "zero_wf"},
        },
        "readout_pulse_2": {
            "operation": "measurement",
            "length": meas_len_2,
            "digital_marker": "ON",
            "waveforms": {"single": "zero_wf"},
        },
        "long_readout_pulse_2": {
            "operation": "measurement",
            "length": long_meas_len_2,
            "digital_marker": "ON",
            "waveforms": {"single": "zero_wf"},
        },
    },
    "waveforms": {
        "cw_wf": {"type": "constant", "sample": mw_amp_NV},
        "rf_const_wf": {"type": "constant", "sample": rf_amp},
        "x180_wf": {"type": "constant", "sample": x180_amp_NV},
        "x90_wf": {"type": "constant", "sample": x90_amp_NV},
        "minus_x90_wf": {"type": "constant", "sample": -x90_amp_NV},
        "zero_wf": {"type": "constant", "sample": 0.0},
    },
    "digital_waveforms": {
        "ON": {"samples": [(1, 0)]},  # [(on/off, ns)]
        "OFF": {"samples": [(0, 0)]},  # [(on/off, ns)]
    },
}
