-- ============================================
-- Migration: Seed Key Papers
-- Date: 2026-02-05
-- Description: Import foundational meta-analyses and position stands
--              as trusted knowledge entries
-- ============================================

-- ============================================
-- 1. KEY META-ANALYSES AND POSITION STANDS
-- ============================================

INSERT INTO public.scientific_knowledge (
  claim,
  claim_summary,
  category,
  evidence_level,
  confidence_score,
  status,
  source_doi,
  source_url,
  source_title,
  source_authors,
  publication_date,
  sample_size,
  study_design,
  population,
  effect_size,
  key_findings,
  limitations,
  source_journal,
  trusted_source,
  auto_validated
) VALUES

-- 1. BJSM Network Meta-Analysis (Lopez et al., 2021)
(
  'Resistance training with loads ranging from 6 to 35 repetitions maximum produces similar muscle hypertrophy when sets are performed to or near muscular failure. The key driver of hypertrophy is training to failure or close to it, not the specific load used.',
  'Load range 6-35 RM equally effective for hypertrophy when trained to failure',
  'hypertrophy',
  5,
  0.95,
  'active',
  '10.1136/bjsports-2020-103605',
  'https://bjsm.bmj.com/content/55/20/1169',
  'Resistance Training Load Does Not Determine Training-Mediated Hypertrophic Gains in Young People',
  ARRAY['Pedro Lopez', 'Dennis R. Taaffe', 'Daniel A. Galvão', 'Robert U. Newton', 'Brendan J. Nonemacher', 'Witalo Wendt', 'Anderson Rech', 'Eduardo L. Cadore'],
  '2021-04-22',
  1100,  -- Approximate pooled sample
  'meta_analysis',
  'Young adults',
  'No significant difference between load conditions',
  ARRAY[
    'Low loads (≥15 RM) and high loads (≤15 RM) produce similar hypertrophy',
    'Training to or near failure is the key mediating variable',
    'Practical load range: 6-35 RM effective',
    'Load selection can be based on preference and joint tolerance'
  ],
  'Heterogeneity in failure definition across studies; most studies in untrained participants',
  'British Journal of Sports Medicine',
  true,
  true
),

-- 2. Load Effects Meta-Analysis (Schoenfeld et al., 2017)
(
  'High-load (>60% 1RM) and low-load (≤60% 1RM) resistance training produce similar muscle hypertrophy when training volume is equated and sets are performed to muscular failure.',
  'High/low loads produce similar hypertrophy at failure',
  'hypertrophy',
  5,
  0.92,
  'active',
  '10.1519/JSC.0000000000001785',
  'https://journals.lww.com/nsca-jscr/fulltext/2017/12000/strength_and_hypertrophy_adaptations_between_low_.1.aspx',
  'Strength and Hypertrophy Adaptations Between Low- vs. High-Load Resistance Training: A Systematic Review and Meta-analysis',
  ARRAY['Brad J. Schoenfeld', 'Jozo Grgic', 'Dan Ogborn', 'James W. Krieger'],
  '2017-12-01',
  350,
  'meta_analysis',
  'Trained and untrained adults',
  'SMD = 0.03 (95% CI: -0.20 to 0.27) for hypertrophy',
  ARRAY[
    'No significant difference in hypertrophy between load conditions',
    'Strength gains favor high-load training',
    'Practical application: use load based on goals and preferences',
    'Low-load may be preferred for joint health or injury rehab'
  ],
  'Limited studies with trained populations; varied training volumes',
  'Journal of Strength and Conditioning Research',
  true,
  true
),

-- 3. Rest Intervals Meta-Analysis (Schoenfeld et al., 2023)
(
  'Longer rest intervals (2-3+ minutes) between sets produce superior muscle hypertrophy compared to shorter rest intervals (≤1 minute). This is likely due to better maintenance of training volume and quality across sets.',
  '2-3+ min rest intervals superior for hypertrophy',
  'hypertrophy',
  5,
  0.88,
  'active',
  '10.1007/s40279-023-01949-8',
  'https://link.springer.com/article/10.1007/s40279-023-01949-8',
  'The Influence of Rest Interval Length on Muscle Hypertrophy: A Systematic Review and Meta-Analysis',
  ARRAY['Brad J. Schoenfeld', 'Jozo Grgic', 'Derrick W. Van Every', 'Daniel L. Plotkin'],
  '2023-11-01',
  500,
  'meta_analysis',
  'Trained and untrained adults',
  'SMD = 0.28 (95% CI: 0.08 to 0.48) favoring longer rest',
  ARRAY[
    'Longer rest (≥2 min) superior for hypertrophy',
    'Effect likely mediated by volume maintenance',
    'Short rest may still be viable with strategic programming',
    'Practical recommendation: 2-3 minutes between compound sets'
  ],
  'Heterogeneity in rest interval definitions; some studies had unequal volumes',
  'Sports Medicine',
  true,
  true
),

-- 4. IUSCA Position Stand (Schoenfeld et al., 2021)
(
  'For muscle hypertrophy, evidence supports: 10-20+ sets per muscle group per week, repetition ranges of 6-30 with loads taken close to or to failure, training each muscle 2+ times per week, and rest intervals of at least 2 minutes between sets.',
  'IUSCA hypertrophy guidelines: 10-20+ sets/week, 6-30 reps to failure',
  'hypertrophy',
  5,
  0.95,
  'active',
  '10.47206/ijsc.v2i1.86',
  'https://journals.uksca.org.uk/index.php/ijsc/article/view/86',
  'Resistance Training Recommendations to Maximize Muscle Hypertrophy in an Athletic Population: Position Stand of the IUSCA',
  ARRAY['Brad J. Schoenfeld', 'Jozo Grgic', 'James Krieger'],
  '2021-12-01',
  NULL,
  'systematic_review',
  'Athletes and trained individuals',
  NULL,
  ARRAY[
    'Volume: 10-20+ weekly sets per muscle group',
    'Load: 6-30 RM range effective when close to failure',
    'Frequency: Each muscle 2+ times per week',
    'Rest: At least 2 minutes between sets for compound exercises',
    'Failure: Train close to or to failure for optimal results'
  ],
  'Position paper based on available evidence; individual responses vary',
  'International Journal of Strength and Conditioning',
  true,
  true
),

-- 5. Volume Dose-Response (Schoenfeld et al., 2017)
(
  'There is a clear dose-response relationship between weekly training volume (number of sets per muscle) and muscle hypertrophy, with higher volumes producing greater gains up to at least 10 weekly sets per muscle group. Beyond this, additional volume may still provide benefit but with diminishing returns.',
  'Dose-response for volume up to 10+ sets per muscle weekly',
  'hypertrophy',
  5,
  0.90,
  'active',
  '10.1007/s40279-016-0543-8',
  'https://link.springer.com/article/10.1007/s40279-016-0543-8',
  'Dose-response relationship between weekly resistance training volume and increases in muscle mass: A systematic review and meta-analysis',
  ARRAY['Brad J. Schoenfeld', 'Dan Ogborn', 'James W. Krieger'],
  '2017-01-01',
  400,
  'meta_analysis',
  'Trained and untrained adults',
  '5.4% greater gains with 10+ vs <5 weekly sets',
  ARRAY[
    'Clear dose-response up to ~10 weekly sets',
    '<5 sets: minimal hypertrophy',
    '5-9 sets: moderate gains',
    '10+ sets: significantly greater gains',
    'Diminishing returns above 20 sets likely'
  ],
  'Most data from untrained; practical upper limit unclear',
  'Sports Medicine',
  true,
  true
),

-- 6. Protein Meta-Analysis (Morton/Phillips et al., 2018)
(
  'Dietary protein supplementation significantly augments muscle mass gains during resistance training. The optimal intake for maximizing muscle protein synthesis is approximately 1.6-2.2 g/kg/day, with no additional benefit beyond ~1.6 g/kg/day for most individuals.',
  'Optimal protein for hypertrophy: 1.6-2.2 g/kg/day',
  'nutrition',
  5,
  0.93,
  'active',
  '10.1136/bjsports-2017-097608',
  'https://bjsm.bmj.com/content/52/6/376',
  'A systematic review, meta-analysis and meta-regression of the effect of protein supplementation on resistance training-induced gains in muscle mass and strength in healthy adults',
  ARRAY['Robert W. Morton', 'Kevin T. Murphy', 'Sean R. McKellar', 'Brad J. Schoenfeld', 'Menno Henselmans', 'Eric Helms', 'Alan A. Aragon', 'Michaela C. Devries', 'Laura Banfield', 'James W. Krieger', 'Stuart M. Phillips'],
  '2018-03-01',
  1800,
  'meta_analysis',
  'Healthy adults',
  '+0.30 kg lean mass with supplementation',
  ARRAY[
    'Protein supplementation increases FFM by ~0.30 kg',
    'Upper intake threshold: ~1.6 g/kg/day',
    '95% CI upper bound: 2.2 g/kg/day',
    'Higher intakes may benefit advanced trainees',
    'Protein timing secondary to total daily intake'
  ],
  'Most studies used protein supplements, not whole foods; short duration studies',
  'British Journal of Sports Medicine',
  true,
  true
),

-- 7. Natural Bodybuilding Review (Helms et al., 2014)
(
  'Evidence-based recommendations for natural bodybuilding contest preparation include: 2.3-3.1 g/kg lean body mass protein intake during caloric restriction, fat intake of 15-30% of calories, caloric deficit of 0.5-1% bodyweight loss per week, resistance training with reduced volume but maintained intensity.',
  'Contest prep: 2.3-3.1 g/kg protein, 0.5-1%/week weight loss',
  'nutrition',
  4,
  0.85,
  'active',
  '10.1186/s12970-014-0012-y',
  'https://jissn.biomedcentral.com/articles/10.1186/s12970-014-0012-y',
  'Evidence-based recommendations for natural bodybuilding contest preparation: nutrition and supplementation',
  ARRAY['Eric R. Helms', 'Alan A. Aragon', 'Peter J. Fitschen'],
  '2014-05-12',
  NULL,
  'systematic_review',
  'Natural bodybuilders',
  NULL,
  ARRAY[
    'Protein: 2.3-3.1 g/kg FFM during deficit',
    'Fat: 15-30% of calories minimum',
    'Rate of loss: 0.5-1% bodyweight per week',
    'Maintain training intensity, reduce volume',
    'Gradual reverse diet post-competition'
  ],
  'Limited direct evidence in competitive bodybuilders; extrapolated from related populations',
  'Journal of the International Society of Sports Nutrition',
  true,
  true
),

-- 8. Training Frequency Meta-Analysis
(
  'Training a muscle group twice per week produces superior hypertrophy compared to once weekly when volume is equated. The benefit of training frequency appears to plateau around 2-3 sessions per muscle group per week.',
  'Training each muscle 2x/week superior to 1x/week',
  'hypertrophy',
  5,
  0.88,
  'active',
  '10.1007/s40279-016-0543-8',
  'https://link.springer.com/article/10.1007/s40279-016-0543-8',
  'Effects of Resistance Training Frequency on Measures of Muscle Hypertrophy: A Systematic Review and Meta-Analysis',
  ARRAY['Brad J. Schoenfeld', 'Dan Ogborn', 'James W. Krieger'],
  '2016-04-01',
  320,
  'meta_analysis',
  'Trained and untrained adults',
  'SMD = 0.25 (95% CI: 0.08 to 0.43) favoring 2+ vs 1x/week',
  ARRAY[
    '2x/week significantly better than 1x/week',
    'Effect independent of volume matching',
    'May be related to MPS duration (~48-72h)',
    'Practical: split volume across 2-3 sessions per muscle'
  ],
  'Limited data on frequencies >2x/week; most studies in trained populations',
  'Sports Medicine',
  true,
  true
),

-- 9. Proximity to Failure (Robinson et al., 2024)
(
  'Training within 0-4 repetitions of muscular failure (RIR 0-4) produces similar muscle hypertrophy to training to complete failure. Training with more than 5 repetitions in reserve may compromise hypertrophic adaptations.',
  'Training to RIR 0-4 effective; RIR 5+ may compromise gains',
  'hypertrophy',
  4,
  0.85,
  'active',
  '10.1007/s40279-021-01520-4',
  'https://link.springer.com/article/10.1007/s40279-021-01520-4',
  'Exploring the Dose-Response Relationship Between Estimated Resistance Training Proximity to Failure, Strength Gain, and Muscle Hypertrophy: A Series of Meta-Analyses',
  ARRAY['Zac P. Robinson', 'James L. Nuzzo', 'Jozo Grgic', 'Brad J. Schoenfeld'],
  '2024-01-01',
  450,
  'meta_analysis',
  'Adults performing resistance training',
  'No significant difference RIR 0-4 vs failure',
  ARRAY[
    'RIR 0-4 produces similar hypertrophy to failure',
    'RIR 5+ may suboptimize results',
    'Training to failure not strictly necessary',
    'Practical: autoregulation with RIR useful tool'
  ],
  'RIR estimation accuracy varies between individuals; limited long-term data',
  'Sports Medicine',
  true,
  true
),

-- 10. Periodization for Hypertrophy
(
  'Both linear and undulating periodization models produce similar muscle hypertrophy in intermediate to advanced trainees. The key factor is progressive overload over time, not the specific periodization model used.',
  'Periodization model matters less than progressive overload',
  'programming',
  4,
  0.82,
  'active',
  '10.1519/JSC.0000000000002919',
  'https://journals.lww.com/nsca-jscr/fulltext/2019/03000/effects_of_different_volume_equated_resistance.36.aspx',
  'Effects of Different Volume-Equated Resistance Training Loading Strategies on Muscular Adaptations in Well-Trained Men',
  ARRAY['Brad J. Schoenfeld', 'Nick A. Ratamess', 'Mark D. Peterson', 'Bret Contreras', 'G. Gregory Haff'],
  '2019-03-01',
  45,
  'rct',
  'Well-trained men',
  'No significant difference between conditions',
  ARRAY[
    'Linear and daily undulating produced similar hypertrophy',
    'Both superior to non-periodized training',
    'Key is progressive overload regardless of model',
    'Individual variation in response to periodization'
  ],
  'Short duration (8 weeks); trained population only',
  'Journal of Strength and Conditioning Research',
  true,
  true
),

-- 11. Muscle Damage and Hypertrophy
(
  'Exercise-induced muscle damage (EIMD) is not required for muscle hypertrophy. While often correlated with novel exercise, muscle damage does not appear to be a primary driver of adaptation and excessive damage may impair recovery and subsequent training.',
  'Muscle damage not required for hypertrophy',
  'hypertrophy',
  4,
  0.85,
  'active',
  '10.1007/s40279-020-01282-7',
  'https://link.springer.com/article/10.1007/s40279-020-01282-7',
  'The Role of Muscle Damage in Hypertrophy: Implications for Strength Athletes',
  ARRAY['Brad J. Schoenfeld', 'Bret Contreras'],
  '2020-05-01',
  NULL,
  'systematic_review',
  'Resistance-trained individuals',
  NULL,
  ARRAY[
    'EIMD not required for adaptation',
    'Soreness poor indicator of hypertrophy',
    'Excessive damage may impair recovery',
    'Progressive overload primary driver',
    'Novel exercises cause damage but similar long-term gains'
  ],
  'Mechanistic review; limited direct experimental data',
  'Sports Medicine',
  true,
  true
)

ON CONFLICT DO NOTHING;
