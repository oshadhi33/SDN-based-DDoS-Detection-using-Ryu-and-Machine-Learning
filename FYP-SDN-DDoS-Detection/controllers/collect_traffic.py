# Import Ryu core components and event handlers
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.lib import hub  # Ryu's built-in thread management library

# Import custom switch logic (likely inherited from SimpleSwitch13)
import switch

# For timestamping and logging
from datetime import datetime

# ML and data processing libraries
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import confusion_matrix, accuracy_score

# Define a new Ryu app class inheriting from custom switch logic
class SimpleMonitor13(switch.SimpleSwitch13):

    def __init__(self, *args, **kwargs):
        # Initialize parent class
        super(SimpleMonitor13, self).__init__(*args, **kwargs)

        # Dictionary to store datapath objects (active switches)
        self.datapaths = {}

        # Start background thread to periodically request stats
        self.monitor_thread = hub.spawn(self._monitor)

        # Train ML model on dataset at controller startup
        start = datetime.now()
        self.flow_training()
        end = datetime.now()
        print("Training time: ", (end - start))

    # Handles state changes in datapaths (switches)
    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def _state_change_handler(self, ev):
        datapath = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            if datapath.id not in self.datapaths:
                self.logger.debug('register datapath: %016x', datapath.id)
                self.datapaths[datapath.id] = datapath
        elif ev.state == DEAD_DISPATCHER:
            if datapath.id in self.datapaths:
                self.logger.debug('unregister datapath: %016x', datapath.id)
                del self.datapaths[datapath.id]

    # Periodic monitoring thread for flow stats and prediction
    def _monitor(self):
        while True:
            for dp in self.datapaths.values():
                self._request_stats(dp)
            hub.sleep(10)  # Wait 10 seconds before next request

            self.flow_predict()  # Run prediction after every stats collection

    # Send flow statistics request to a switch
    def _request_stats(self, datapath):
        self.logger.debug('send stats request: %016x', datapath.id)
        parser = datapath.ofproto_parser
        req = parser.OFPFlowStatsRequest(datapath)
        datapath.send_msg(req)

    # Handle flow statistics reply event
    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def _flow_stats_reply_handler(self, ev):
        timestamp = datetime.now().timestamp()

        # Create or overwrite flow stats file
        file0 = open("FlowStatsfile.csv", "w")
        file0.write('timestamp,datapath_id,flow_id,ip_src,tp_src,ip_dst,tp_dst,ip_proto,icmp_code,icmp_type,flow_duration_sec,flow_duration_nsec,idle_timeout,hard_timeout,flags,packet_count,byte_count,packet_count_per_second,packet_count_per_nsecond,byte_count_per_second,byte_count_per_nsecond\n')

        # Process each flow entry
        body = ev.msg.body
        icmp_code, icmp_type, tp_src, tp_dst = -1, -1, 0, 0

        for stat in sorted([flow for flow in body if flow.priority == 1],
                           key=lambda flow: (flow.match['eth_type'], flow.match['ipv4_src'], flow.match['ipv4_dst'], flow.match['ip_proto'])):
            ip_src = stat.match['ipv4_src']
            ip_dst = stat.match['ipv4_dst']
            ip_proto = stat.match['ip_proto']

            # Extract protocol-specific values
            if ip_proto == 1:
                icmp_code = stat.match.get('icmpv4_code', -1)
                icmp_type = stat.match.get('icmpv4_type', -1)
            elif ip_proto == 6:
                tp_src = stat.match.get('tcp_src', 0)
                tp_dst = stat.match.get('tcp_dst', 0)
            elif ip_proto == 17:
                tp_src = stat.match.get('udp_src', 0)
                tp_dst = stat.match.get('udp_dst', 0)

            flow_id = f"{ip_src}{tp_src}{ip_dst}{tp_dst}{ip_proto}"

            # Calculate traffic rates
            try:
                packet_count_per_second = stat.packet_count / stat.duration_sec
                packet_count_per_nsecond = stat.packet_count / stat.duration_nsec
            except:
                packet_count_per_second, packet_count_per_nsecond = 0, 0

            try:
                byte_count_per_second = stat.byte_count / stat.duration_sec
                byte_count_per_nsecond = stat.byte_count / stat.duration_nsec
            except:
                byte_count_per_second, byte_count_per_nsecond = 0, 0

            # Write flow features to file
            file0.write("{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{}\n"
                .format(timestamp, ev.msg.datapath.id, flow_id, ip_src, tp_src, ip_dst, tp_dst,
                        ip_proto, icmp_code, icmp_type,
                        stat.duration_sec, stat.duration_nsec,
                        stat.idle_timeout, stat.hard_timeout,
                        stat.flags, stat.packet_count, stat.byte_count,
                        packet_count_per_second, packet_count_per_nsecond,
                        byte_count_per_second, byte_count_per_nsecond))
        file0.close()

    # Train the machine learning model on labeled flow data
    def flow_training(self):
        self.logger.info("***** Flow Training *****")
        flow_dataset = pd.read_csv('final_fyp.csv')

        # Remove dots from IP addresses to make them numeric strings
        flow_dataset.iloc[:, 2] = flow_dataset.iloc[:, 2].str.replace('.', '')
        flow_dataset.iloc[:, 3] = flow_dataset.iloc[:, 3].str.replace('.', '')
        flow_dataset.iloc[:, 5] = flow_dataset.iloc[:, 5].str.replace('.', '')

        # Split into features and target
        X_flow = flow_dataset.iloc[:, :-1].values.astype('float64')
        y_flow = flow_dataset.iloc[:, -1].values

        # Split into training and testing sets
        X_flow_train, X_flow_test, y_flow_train, y_flow_test = train_test_split(
            X_flow, y_flow, test_size=0.25, random_state=0)

        # Train Random Forest model
        classifier = RandomForestClassifier(n_estimators=10, criterion="entropy", random_state=0)
        self.flow_model = classifier.fit(X_flow_train, y_flow_train)

        # Evaluate model
        y_flow_pred = self.flow_model.predict(X_flow_test)
        self.logger.info("============================================================================")
        self.logger.info(" ")
        self.logger.info("Confusion Matrix")
        cm = confusion_matrix(y_flow_test, y_flow_pred)
        self.logger.info(cm)
        acc = accuracy_score(y_flow_test, y_flow_pred)
        self.logger.info(" ")
        self.logger.info("Model Accuracy = {0:.2f} %".format(acc * 100))
        self.logger.info("Fail Accuracy = {0:.2f} %".format((1.0 - acc) * 100))
        self.logger.info("============================================================================")

    # Predict whether traffic is legitimate or DDoS based on collected flow stats
    def flow_predict(self):
        try:
            predict_flow_dataset = pd.read_csv('FlowStatsfile.csv')

            # Preprocess IPs
            predict_flow_dataset.iloc[:, 2] = predict_flow_dataset.iloc[:, 2].str.replace('.', '')
            predict_flow_dataset.iloc[:, 3] = predict_flow_dataset.iloc[:, 3].str.replace('.', '')
            predict_flow_dataset.iloc[:, 5] = predict_flow_dataset.iloc[:, 5].str.replace('.', '')

            X_predict_flow = predict_flow_dataset.values.astype('float64')
            y_flow_pred = self.flow_model.predict(X_predict_flow)

            # Count traffic categories
            legitimate_traffic = sum(1 for i in y_flow_pred if i == 0)
            ddos_traffic = sum(1 for i in y_flow_pred if i != 0)

            self.logger.info("============================================================================")
            self.logger.info(" ")

            if (legitimate_traffic / len(y_flow_pred) * 100) > 80:
                self.logger.info("***************** Legitimate Traffic *****************")
            else:
                self.logger.info("!!!!!!!!!!!!!!!!!!!! DDoS Traffic !!!!!!!!!!!!!!!!!!!!")
                victim = int(predict_flow_dataset.iloc[i, 5]) % 20  # Identify victim based on dst IP
                self.logger.info("Victim is Host: h{}".format(victim))
                print("Mitigation process in progress!")
                self.mitigation = 1  # Set mitigation flag

            self.logger.info(" ")
            self.logger.info("============================================================================")

            # Clear the flow stats file to avoid duplicate processing
            file0 = open("PredictFlowStatsfile.csv", "w")
            file0.write('timestamp,datapath_id,flow_id,ip_src,tp_src,ip_dst,tp_dst,ip_proto,icmp_code,icmp_type,flow_duration_sec,flow_duration_nsec,idle_timeout,hard_timeout,flags,packet_count,byte_count,packet_count_per_second,packet_count_per_nsecond,byte_count_per_second,byte_count_per_nsecond\n')
            file0.close()

        except:
            pass  # Fail silently if file not found or prediction fails
