# sip-call-handler/sip_handler/sip_client.py

import pjsua2 as pj

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
        # First, discover our public IP
        public_ip = get_public_ip()
        if not public_ip:
            raise RuntimeError("Cannot start SIP client without a public IP address.")

        self.ep.libCreate()
        
        ep_cfg = pj.EpConfig()
        ep_cfg.logConfig.level = 4
        ep_cfg.logConfig.consoleLevel = 4
        
        # STUN is still useful for NAT type detection, so we keep it
        stun_servers = pj.StringVector()
        stun_servers.append("stun.l.google.com:19302")
        ep_cfg.uaConfig.stunServer = stun_servers

        self.ep.libInit(ep_cfg)

        # Create SIP transport
        transport_cfg = pj.TransportConfig()
        transport_cfg.port = 5060

        # Set the discovered public address
        transport_cfg.public_addr = public_ip

        self.ep.transportCreate(pj.PJSIP_TRANSPORT_UDP, transport_cfg)

        self.ep.libStart()
        print("*** PJSUA2 started ***")

        # Create and register account
        acc_cfg = pj.AccountConfig()
        acc_cfg.idUri = f"sip:{self.config.SIP_USER}@{self.config.SIP_DOMAIN}"
        acc_cfg.regConfig.registrarUri = f"sip:{self.config.SIP_DOMAIN}"
        cred = pj.AuthCredInfo("digest", "*", self.config.SIP_USER, 0, self.config.SIP_PASSWORD)
        acc_cfg.sipConfig.authCreds.append(cred)

        self.acc = self._create_account(acc_cfg)
        print(f"*** Account {self.acc.getInfo().uri} registered ***")


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
        remote_uri = prm.remoteUri
        print(f"*** Incoming call from {remote_uri} ***")
        call = Call(self, self.client, call_id=prm.callId)
        self.client.current_call = call
        
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
            if self.client.dtmf_callback and self.dtmf_buffer:
                self.client.dtmf_callback(self.dtmf_buffer)
            self.dtmf_buffer = "" # Reset buffer
        else:
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
        # ... (this method is unchanged) ...
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