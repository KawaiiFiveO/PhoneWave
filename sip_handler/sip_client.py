# sip-call-handler/sip_handler/sip_client.py

import pjsua2 as pj
import requests

def get_public_ip():
    """Fetches the public IP address from an external service."""
    try:
        response = requests.get('https://api.ipify.org')
        response.raise_for_status()
        print(f"Discovered public IP: {response.text}")
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Could not get public IP address: {e}")
        return None

class SipClient:
    def __init__(self, config, dtmf_callback=None, disconnect_callback=None):
        self.config = config
        self.dtmf_callback = dtmf_callback
        self.disconnect_callback = disconnect_callback
        self.ep = pj.Endpoint()
        self.acc = None
        self.current_call = None

    def start(self):
        public_ip = get_public_ip()
        if not public_ip:
            raise RuntimeError("Cannot start SIP client without a public IP address.")

        self.ep.libCreate()
        
        ep_cfg = pj.EpConfig()
        ep_cfg.uaConfig.maxCalls = 1
        ep_cfg.uaConfig.userAgent = "PhoneWave SIP Client v1.0"

        media_cfg = pj.MediaConfig()
        media_cfg.enableVad = False
        ep_cfg.mediaConfig = media_cfg
        
        stun_servers = pj.StringVector()
        stun_servers.append("stun.l.google.com:19302")
        ep_cfg.uaConfig.stunServer = stun_servers

        self.ep.libInit(ep_cfg)

        # 1. Create a UDP transport on the standard port
        transport_cfg = pj.TransportConfig()
        transport_cfg.port = 5060
        # 2. Advertise our public IP in SIP messages
        transport_cfg.public_addr = public_ip
        self.ep.transportCreate(pj.PJSIP_TRANSPORT_UDP, transport_cfg)

        self.ep.libStart()
        print("*** PJSUA2 started with UDP transport ***")

        # Create and register account
        acc_cfg = pj.AccountConfig()
        acc_cfg.idUri = f"sip:{self.config.SIP_USER}@{self.config.SIP_DOMAIN}"
        acc_cfg.regConfig.registrarUri = f"sip:{self.config.SIP_DOMAIN}"
        
        cred = pj.AuthCredInfo("digest", "*", self.config.SIP_USER, 0, self.config.SIP_PASSWORD)
        acc_cfg.sipConfig.authCreds.append(cred)

        # 3. Set the outbound proxy for robust call matching
        outbound_proxy_vector = pj.StringVector()
        outbound_proxy_vector.append(f"sip:{self.config.SIP_DOMAIN};lr")
        acc_cfg.sipConfig.outboundProxies = outbound_proxy_vector

        # 4. Use AccountNatConfig to force the correct 'Via' header during authentication
        acc_nat_cfg = pj.AccountNatConfig()
        acc_nat_cfg.via_addr = public_ip
        acc_cfg.natConfig = acc_nat_cfg

        self.acc = self._create_account(acc_cfg)
        print(f"*** Account {acc_cfg.idUri} registered ***")

    def stop(self):
        if self.ep:
            self.ep.libDestroy()
            print("*** PJSUA2 shut down ***")

    def _create_account(self, acc_cfg):
        account = Account(self)
        account.create(acc_cfg)
        return account

class Account(pj.Account):
    def __init__(self, client):
        pj.Account.__init__(self)
        self.client = client

    def onIncomingCall(self, prm):
        print("!!! onIncomingCall HAS BEEN TRIGGERED !!!")
        
        # 1. Create the Call object from the callId provided in the prm object.
        call = Call(self, self.client, call_id=prm.callId)
        self.client.current_call = call
        
        # 2. Get the call's information FROM the call object.
        try:
            ci = call.getInfo()
            remote_info = ci.remoteUri
            print(f"*** Incoming call from {remote_info} ***")
        except pj.Error as e:
            print(f"Error getting call info: {e}")
            # Hang up if we can't get info
            call.hangup(pj.CallOpParam(500))
            return

        # 3. Answer the call.
        call_prm = pj.CallOpParam()
        call_prm.statusCode = 200
        call.answer(call_prm)

class Call(pj.Call):
    def __init__(self, acc, client, call_id=pj.PJSUA_INVALID_ID):
        pj.Call.__init__(self, acc, call_id)
        self.client = client
        self.player = None
        self.dtmf_buffer = ""

    def onDtmfDigit(self, prm):
        digit = prm.digit
        print(f"*** DTMF digit received: {digit} ***")

        if digit == '#':
            # If # is pressed, send the whole buffer to the callback
            if self.client.dtmf_callback and self.dtmf_buffer:
                self.client.dtmf_callback(self.dtmf_buffer)
            # Always reset the buffer after # is pressed
            self.dtmf_buffer = ""
        else:
            # If any other digit is pressed, add it to the buffer
            self.dtmf_buffer += digit

    def onCallState(self, prm):
        ci = self.getInfo()
        print(f"*** Call state changed to {ci.stateText} ***")
        if ci.state == pj.PJSIP_INV_STATE_DISCONNECTED:
            print("*** Call disconnected ***")
            self.client.current_call = None
            self.player = None
            if self.client.disconnect_callback:
                self.client.disconnect_callback()

    def onCallMediaState(self, prm):
        ci = self.getInfo()
        print("*** Call media state changed ***")
        for mi in ci.media:
            if mi.type == pj.PJMEDIA_TYPE_AUDIO and mi.status == pj.PJSUA_CALL_MEDIA_ACTIVE:
                try:
                    self.player = pj.AudioMediaPlayer()
                    self.player.createPlayer(self.client.config.WAV_FILE, pj.PJMEDIA_FILE_NO_LOOP)
                    call_media = self.getAudioMedia(mi.index)
                    self.player.startTransmit(call_media)
                    print(f"*** Playing {self.client.config.WAV_FILE} ***")
                except pj.Error as e:
                    print(f"Error creating or playing WAV file: {e}")
                    self.player = None