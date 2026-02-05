-- ============================================
-- Migration: Seed Authoritative Sources
-- Date: 2026-02-05
-- Description: Populate trusted authors and journals
-- ============================================

-- ============================================
-- 1. SEED TRUSTED JOURNALS
-- ============================================

INSERT INTO public.trusted_journals (name, short_name, normalized_name, issn, eissn, publisher, priority_boost, impact_factor, rss_feed_url, notes) VALUES

-- Tier 1: Top strength & conditioning journals (boost 3)
(
  'Journal of Strength and Conditioning Research',
  'JSCR',
  'journal of strength and conditioning research',
  '1064-8011',
  '1533-4287',
  'Wolters Kluwer',
  3,
  3.0,
  NULL,
  'Primary S&C research journal, NSCA flagship'
),
(
  'Journal of Applied Physiology',
  'JAP',
  'journal of applied physiology',
  '8750-7587',
  '1522-1601',
  'American Physiological Society',
  3,
  3.3,
  'https://journals.physiology.org/action/showFeed?type=etoc&feed=rss&jc=jappl',
  'Top physiology journal, excellent exercise research'
),
(
  'Sports Medicine',
  'SM',
  'sports medicine',
  '0112-1642',
  '1179-2035',
  'Springer',
  3,
  11.1,
  'https://link.springer.com/search.rss?facet-content-type=Article&facet-journal-id=40279&channel-name=Sports+Medicine',
  'High-impact reviews and meta-analyses'
),
(
  'British Journal of Sports Medicine',
  'BJSM',
  'british journal of sports medicine',
  '0306-3674',
  '1473-0480',
  'BMJ',
  3,
  18.5,
  'https://bjsm.bmj.com/rss/current.xml',
  'Excellent for evidence-based guidelines'
),
(
  'International Journal of Strength and Conditioning',
  'IJSC',
  'international journal of strength and conditioning',
  NULL,
  NULL,
  'UKSCA',
  3,
  NULL,
  NULL,
  'UKSCA journal, practical S&C research'
),
(
  'International Journal of Sports Physiology and Performance',
  'IJSPP',
  'international journal of sports physiology and performance',
  '1555-0265',
  '1555-0273',
  'Human Kinetics',
  3,
  3.5,
  NULL,
  'Strong performance and training research'
),

-- Tier 2: Good specialty journals (boost 2)
(
  'Frontiers in Sports and Active Living',
  'FSAL',
  'frontiers in sports and active living',
  NULL,
  '2624-9367',
  'Frontiers',
  2,
  2.6,
  'https://www.frontiersin.org/journals/sports-and-active-living/rss',
  'Open access, good recent research'
),
(
  'Frontiers in Physiology',
  'FP',
  'frontiers in physiology',
  NULL,
  '1664-042X',
  'Frontiers',
  2,
  4.0,
  'https://www.frontiersin.org/journals/physiology/rss',
  'Open access physiology journal'
),
(
  'European Journal of Sport Science',
  'EJSS',
  'european journal of sport science',
  '1746-1391',
  '1536-7290',
  'Taylor & Francis',
  2,
  3.5,
  NULL,
  'European sport science research'
),
(
  'Scandinavian Journal of Medicine and Science in Sports',
  'SJMSS',
  'scandinavian journal of medicine and science in sports',
  '0905-7188',
  '1600-0838',
  'Wiley',
  2,
  4.1,
  NULL,
  'Strong Scandinavian research tradition'
),
(
  'Medicine and Science in Sports and Exercise',
  'MSSE',
  'medicine and science in sports and exercise',
  '0195-9131',
  '1530-0315',
  'Wolters Kluwer',
  2,
  6.3,
  NULL,
  'ACSM flagship journal'
),
(
  'Journal of Sports Sciences',
  'JSS',
  'journal of sports sciences',
  '0264-0414',
  '1466-447X',
  'Taylor & Francis',
  2,
  3.5,
  NULL,
  'Broad sports science research'
),

-- Nutrition journals (boost 2)
(
  'Journal of the International Society of Sports Nutrition',
  'JISSN',
  'journal of the international society of sports nutrition',
  '1550-2783',
  NULL,
  'BioMed Central',
  2,
  5.1,
  NULL,
  'ISSN flagship, sports nutrition focus'
),
(
  'American Journal of Clinical Nutrition',
  'AJCN',
  'american journal of clinical nutrition',
  '0002-9165',
  '1938-3207',
  'Oxford Academic',
  2,
  7.0,
  NULL,
  'Top nutrition journal'
),
(
  'Nutrients',
  'Nutrients',
  'nutrients',
  NULL,
  '2072-6643',
  'MDPI',
  2,
  5.7,
  'https://www.mdpi.com/rss/journal/nutrients',
  'Open access, good nutrition research'
)

ON CONFLICT DO NOTHING;

-- ============================================
-- 2. SEED TRUSTED AUTHORS
-- ============================================

INSERT INTO public.trusted_authors (name, normalized_name, affiliation, lab_name, research_areas, priority_boost, orcid, h_index, notes) VALUES

-- Tier 1: Leading researchers (boost 4)
(
  'Brad J. Schoenfeld',
  'brad schoenfeld',
  'Lehman College, CUNY',
  'Human Performance Lab',
  ARRAY['hypertrophy', 'strength', 'training volume', 'resistance training'],
  4,
  '0000-0003-4886-7227',
  65,
  'Leading hypertrophy researcher, prolific meta-analysis author'
),
(
  'Stuart M. Phillips',
  'stuart phillips',
  'McMaster University',
  'Physical Activity Centre of Excellence',
  ARRAY['protein', 'muscle protein synthesis', 'nutrition', 'aging'],
  4,
  '0000-0002-1956-4098',
  95,
  'World-leading MPS researcher'
),

-- Tier 2: Highly cited researchers (boost 3)
(
  'Jozo Grgic',
  'jozo grgic',
  'Victoria University',
  NULL,
  ARRAY['hypertrophy', 'caffeine', 'resistance training', 'training frequency'],
  3,
  '0000-0002-4782-3420',
  35,
  'Prolific meta-analysis author, training optimization'
),
(
  'Daniel R. Moore',
  'daniel moore',
  'University of Toronto',
  'Muscle Health Research Centre',
  ARRAY['protein', 'recovery', 'muscle protein synthesis'],
  3,
  '0000-0003-2965-5005',
  45,
  'Protein timing and distribution expert'
),
(
  'Kevin D. Tipton',
  'kevin tipton',
  'University of Stirling',
  NULL,
  ARRAY['nutrition', 'protein', 'exercise metabolism'],
  3,
  NULL,
  60,
  'Sports nutrition pioneer'
),
(
  'Luc J.C. van Loon',
  'luc van loon',
  'Maastricht University',
  'Department of Human Biology',
  ARRAY['nutrition', 'protein', 'muscle metabolism', 'aging'],
  3,
  '0000-0002-6768-9231',
  85,
  'Leading protein metabolism researcher'
),
(
  'Eric Helms',
  'eric helms',
  'Auckland University of Technology',
  '3D Muscle Journey',
  ARRAY['bodybuilding', 'nutrition', 'contest prep', 'resistance training'],
  3,
  '0000-0002-4012-4566',
  25,
  'Natural bodybuilding evidence-based pioneer'
),
(
  'Greg Nuckols',
  'greg nuckols',
  'Stronger by Science',
  NULL,
  ARRAY['strength', 'powerlifting', 'programming', 'statistics'],
  3,
  NULL,
  NULL,
  'Excellent evidence interpretation, MASS Research Review'
),
(
  'Mike Israetel',
  'mike israetel',
  'Renaissance Periodization',
  NULL,
  ARRAY['hypertrophy', 'volume', 'programming', 'recovery'],
  3,
  NULL,
  NULL,
  'Training volume and periodization expert'
),
(
  'James Krieger',
  'james krieger',
  'Weightology',
  NULL,
  ARRAY['statistics', 'meta-analysis', 'training volume', 'nutrition'],
  3,
  NULL,
  15,
  'Statistical analysis expert, Weightology founder'
),

-- Additional researchers (boost 2)
(
  'Andrew Vigotsky',
  'andrew vigotsky',
  'Northwestern University',
  NULL,
  ARRAY['biomechanics', 'hypertrophy', 'EMG', 'statistics'],
  2,
  '0000-0003-3166-0688',
  15,
  'Biomechanics and statistics expert'
),
(
  'Felipe Damas',
  'felipe damas',
  'University of Sao Paulo',
  NULL,
  ARRAY['hypertrophy', 'muscle damage', 'resistance training'],
  2,
  NULL,
  20,
  'Muscle damage and adaptation research'
),
(
  'James Fisher',
  'james fisher',
  'Southampton Solent University',
  NULL,
  ARRAY['resistance training', 'training to failure', 'intensity'],
  2,
  NULL,
  25,
  'HIT and training intensity research'
),
(
  'Paulo Gentil',
  'paulo gentil',
  'Federal University of Goias',
  NULL,
  ARRAY['hypertrophy', 'training volume', 'resistance training'],
  2,
  '0000-0003-3408-0200',
  30,
  'Training volume research'
),
(
  'Menno Henselmans',
  'menno henselmans',
  'Bayesian Bodybuilding',
  NULL,
  ARRAY['hypertrophy', 'programming', 'nutrition'],
  2,
  NULL,
  NULL,
  'Evidence-based bodybuilding, Bayesian methods'
),
(
  'Jacob Schoenfeld',
  'jacob schoenfeld',
  NULL,
  NULL,
  ARRAY['hypertrophy', 'strength'],
  2,
  NULL,
  NULL,
  'Note: Different from Brad J. Schoenfeld'
),
(
  'Bret Contreras',
  'bret contreras',
  'Auckland University of Technology',
  'Glute Lab',
  ARRAY['glutes', 'hip extension', 'EMG', 'biomechanics'],
  2,
  NULL,
  20,
  'Hip extension and glute training specialist'
),
(
  'Chris Beardsley',
  'chris beardsley',
  'Strength and Conditioning Research',
  NULL,
  ARRAY['biomechanics', 'hypertrophy', 'strength'],
  2,
  NULL,
  NULL,
  'Excellent research interpretation and communication'
)

ON CONFLICT DO NOTHING;
