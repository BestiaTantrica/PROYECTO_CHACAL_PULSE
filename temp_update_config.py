#!/usr/bin/env python3
import json

with open('/home/ec2-user/freqtrade/user_data/config.json', 'r') as f:
    config = json.load(f)

config['strategy'] = 'ChacalPulseV4_Lateral'

with open('/home/ec2-user/freqtrade/user_data/config.json', 'w') as f:
    json.dump(config, f, indent=4)

print('Estrategia actualizada')
