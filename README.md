1. First install requirements with pip:
   pip install -r requirements.txt
2. To generate user & pass file for importing into IBSng run this, then import userpass.csv to IBSng:
   python utils.py USER_NUMBER
3. To start traffic generator run:
   python session.py USER_NUMBER
4. To see graphs run this, then goto http://127.0.0.1:8888:
   python web.py
5. Change configs from config.py
