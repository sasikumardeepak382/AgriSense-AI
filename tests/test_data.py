from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.app.data import load_data

def test_bundled_csv_loads():
 d=load_data(); assert len(d)>1000; assert {'date','commodity','market','modal_price'}.issubset(d.columns)
 assert d.date.nunique()==1
