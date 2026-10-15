1. Paulblade gives raw json
2. Place Paulblade's raw json in the data/results directory
3. Update AppConfig RAW path to point to the new file
4. Auto setup and check:
```bash
./setup.sh
```
5. Otherwise run:
```bash
python -m venv venv
source venv/bin/activate #Mac/Linux 
source venv\Scripts\activate #Windows
pip install -r requirements.txt
python -m src.application.setup
```
5. wait for setup to parse and store curated results.json and download videos to the data/videos directory
6. Any failures -> run `python -m src.application.setup` again to retry failed downloads (skip already downloaded videos)
7. Run the app
```bash
./run.sh
```
- or
```bash
python -m src.application.app
```
8. Terminal will show the URL to open in your browser
```bash
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5000
 * Running on http://100.106.234.129:5000
 ```