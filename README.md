# SDN-based DDoS Detection using Ryu and Machine Learning

## 📌 Overview

This Final Year Project (FYP) implements a **Software Defined Networking (SDN)** based approach to detect **DDoS attacks** using **machine learning models** integrated into a **Ryu OpenFlow controller**.

The controller periodically collects flow statistics from OpenFlow switches, extracts traffic features, and classifies traffic as **legitimate** or **DDoS** using different ML algorithms.

## 🧠 Machine Learning Models Implemented

The project evaluates multiple classifiers for DDoS detection:

| File                     | Model                        |
| ------------------------ | ---------------------------- |
| `collect_traffic.py`     | Baseline                     |
| `collect_traffic_DT.py`  | Decision Tree                |
| `collect_traffic_RFM.py` | Random Forest                |
| `collect_traffic_MLP.py` | Multi-Layer Perceptron (MLP) |
| `collect_traffic_NLP.py` | MLP (variant)                |

Each controller:

* Trains the ML model at startup using a labeled dataset
* Collects live flow statistics every 10 seconds
* Predicts traffic type in real time
* Logs alerts when DDoS traffic is detected

## 🏗️ Project Structure

```
FYP-SDN-DDoS-Detection/
├── controllers/
│   ├── collect_traffic.py
│   ├── collect_traffic_DT.py
│   ├── collect_traffic_RFM.py
│   ├── collect_traffic_MLP.py
│   ├── collect_traffic_NLP.py
│   └── switch.py
├── mininet/
│   └── topology.py
├── dataset/
│   └── final_fyp.csv
├── output/
│   ├── FlowStatsfile.csv
│   └── PredictFlowStatsfile.csv
├── requirements.txt
├── README.md
└── .gitignore
```

## ⚙️ Requirements

* Python 3.8+
* Ryu SDN Framework
* Mininet
* Open vSwitch

### Python Libraries

```
pandas
scikit-learn
numpy
```

## 📊 Dataset Creation and Labeling

The dataset used in this project was custom-built using an SDN-based experimental environment rather than relying solely on public datasets. This ensures that the collected data closely matches the actual network behavior observed in the proposed SDN architecture.

### 1️⃣ SDN Experimental Setup

The dataset generation environment consists of:
- Ryu SDN Controller running on a dedicated host
- Mininet for network emulation
- Open vSwitch (OVS) with OpenFlow 1.3
- Remote controller communication over TCP

The Ryu controller is started with an explicit controller IP and port, allowing Mininet switches to connect remotely:
```
ryu-manager --ofp-tcp-listen-port 6653 \
            --ofp-listen-host 192.168.29.52 \
            collect_traffic.py
```
The Mininet topology is launched separately and connects to the remote controller:
```
sudo python3 topology.py \
     --controller=remote,ip=192.168.29.52,port=6653 \
     --switch=ovs
```
This configuration closely resembles a real-world SDN deployment, where the control plane is separated from the data plane.

### 2️⃣ Traffic Generation

Two categories of traffic were generated to build a balanced dataset:

#### a) Normal Traffic

Normal traffic represents legitimate network usage and includes:

- ICMP echo requests (ping)
- TCP-based application traffic (iperf)
- UDP background traffic

This traffic establishes baseline flow behavior under non-attack conditions.

#### b) DDoS Attack Traffic

Distributed Denial-of-Service (DDoS) traffic was generated using multiple hosts to simulate realistic attack scenarios:
- ICMP Flood – high-rate echo requests
- TCP SYN Flood – excessive connection attempts
- UDP Flood – high-volume stateless packet transmission

Attack traffic was generated using tools such as hping3 and custom scripts, with multiple sources targeting one or more victims.

### 3️⃣ Feature Extraction

Raw OpenFlow flow statistics were transformed into ML-ready features, including:
- Packet count
- Byte count
- Flow duration
- Packets per second (PPS)
- Bytes per second (BPS)
- Average packet size
- Protocol and port information

These features were extracted at fixed time intervals to capture both steady-state and burst-based traffic patterns.

### 4️⃣ Data Labeling

Each flow entry was labeled based on the traffic type:
- Label 0 → Normal traffic
- Label 1 → DDoS traffic

Labeling was performed using:
- The known traffic generation source (normal vs attack hosts)
- Time-based correlation between attack execution and flow statistics
- Protocol and traffic rate characteristics

This labeling approach ensures accurate ground truth without packet-level inspection.

### 5️⃣ Dataset Preparation

Before training the ML models:
- Incomplete and short-lived flows were filtered
- Irrelevant fields were removed
- Features were normalized where required

The final dataset was exported as:
- dataset/final_fyp.csv

This dataset is loaded by the controller at startup for offline training and real-time inference.

### 6️⃣ Advantages of the Custom Dataset

- Reflects real SDN control-plane behavior
- Captures realistic flow dynamics under attack
- Avoids mismatch between public datasets and SDN flow statistics
- Easily extensible for future attack types


## 🚀 How to Run

### 1️⃣ Start Ryu Controller

Run one of the ML-based controllers (example: Random Forest):

```bash
ryu-manager --ofp-tcp-listen-port 6653 \
            --ofp-listen-host 192.168.29.52 \
            collect_traffic_RFM.py

```

### 2️⃣ Start Mininet Topology

In a separate terminal:

```bash
sudo python3 topology.py \
     --controller=remote,ip=192.168.29.52,port=6653 \
     --switch=ovs
```

The topology connects **18 hosts across 6 OpenFlow switches** to a **remote Ryu controller**.

### 3️⃣ Generate Traffic

Use tools such as:

* `iperf`
* `hping3` (for DDoS simulation)
* custom traffic scripts

The controller will automatically collect flow statistics and classify traffic every 10 seconds.


## 🌐 Mininet Topology

The Mininet topology (`topology.py`) creates:

* **6 OpenFlow switches (s1–s6)** connected linearly
* **18 hosts (3 hosts per switch)**
* A **remote Ryu controller** connected via OpenFlow 1.3

Each host is assigned:

* Static IP: `10.0.0.x/24`
* Unique MAC address

This topology is designed to simulate **east–west traffic** and distributed attack patterns.

## 🔁 Ryu Learning Switch (`switch.py`)

The `switch.py` module implements a **Layer-2 learning switch** using **OpenFlow 1.3**, which acts as the base forwarding logic for all ML-based controllers.

### Key Responsibilities

* Handles **Packet-In** events from switches
* Learns MAC-to-port mappings dynamically
* Installs **protocol-aware flow rules** (ICMP, TCP, UDP)
* Reduces controller overhead by proactively installing flows

### Flow Rule Characteristics

* Priority: `1`
* Idle Timeout: `20s`
* Hard Timeout: `100s`

## 🔍 ML-Based Detection Workflow
* Flow Creation via Packet-In events
* Periodic Flow Statistics Collection (OFPFlowStatsRequest)
* Feature Extraction (PPS, BPS, duration, packet size)
* ML Classification (Normal vs DDoS)
* Alerting & Mitigation Trigger
* DDoS is flagged when malicious flows exceed a 20% threshold.

## 🛡️ Future Improvements

* Automatic mitigation (flow rule insertion)
* Online / incremental learning
* Feature normalization consistency in live prediction
* REST API for alerts

## 🎓 Academic Context

This project was developed as a **Final Year Undergraduate Project** in **Information and Communication Engineering**, focusing on:

* SDN security
* Network traffic analysis
* Machine learning for cybersecurity

## 📜 License

This project is released for **academic and educational purposes**.

---

⭐ If you find this project useful, feel free to star the repository!
