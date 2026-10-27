import tempfile
import unittest
import pandas as pd
from analyze import prepare, summarize, run

class AnalysisTests(unittest.TestCase):
    def sample(self):
        return pd.DataFrame({'contact':['cellular']*4, 'month':['may']*4,
            'poutcome':['unknown']*4, 'campaign':[1,2,6,7], 'y':['yes','no','yes','no']})
    def test_rates_and_boundaries(self):
        d = prepare(self.sample())
        self.assertEqual(list(d.campaign_band.astype(str)), ['1','2–3','4–6','7+'])
        t = summarize(d, 'contact')
        self.assertEqual(t.records.iloc[0], 4)
        self.assertEqual(t.response_rate.iloc[0], .5)
    def test_invalid_counts(self):
        for value in [0, -1, 1.5, float('inf')]:
            d = self.sample(); d.loc[0,'campaign'] = value
            with self.assertRaises(ValueError): prepare(d)
    def test_missing_and_invalid_target(self):
        for value in [None, 'maybe']:
            d = self.sample(); d.loc[0,'y'] = value
            with self.assertRaises(ValueError): prepare(d)
        with self.assertRaises(ValueError): prepare(self.sample().iloc[:0])
    def test_outputs(self):
        with tempfile.TemporaryDirectory() as path:
            a = run(self.sample(), path)
            self.assertEqual(a['subscriptions'], 2)
            self.assertEqual(a['unknown_categories']['poutcome'], 4)
            t = pd.read_csv(path+'/segment_summary.csv')
            self.assertTrue((t.groupby('dimension').records.sum() == 4).all())

if __name__ == '__main__': unittest.main()
