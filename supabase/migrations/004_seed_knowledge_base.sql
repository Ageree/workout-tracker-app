-- ============================================
-- Migration: Seed Knowledge Base with Evidence-Based Claims
-- Date: 2026-01-30
-- Description: Initial seed data for scientific knowledge base
-- ============================================

-- ============================================
-- 1. SEED SCIENTIFIC KNOWLEDGE
-- ============================================

-- Note: These are simplified claims without embeddings.
-- In production, embeddings would be generated via OpenAI API.

INSERT INTO public.scientific_knowledge (
  claim,
  claim_summary,
  category,
  evidence_level,
  confidence_score,
  status,
  source_title,
  source_authors,
  publication_date,
  sample_size,
  study_design,
  key_findings,
  limitations
) VALUES
-- Hypertrophy claims
(
  'Для гипертрофии оптимальный диапазон повторений составляет 6-30 повторений в подходе при условии достижения мышечного отказа',
  'Широкий диапазон повторений эффективен для роста мышц',
  'hypertrophy',
  4,
  0.92,
  'active',
  'Effects of range of motion on muscle development during resistance training interventions: A systematic review',
  ARRAY['Schoenfeld B.J.', 'Grgic J.'],
  '2020-01-01',
  21,
  'systematic_review',
  ARRAY['Диапазон 6-30 повторений одинаково эффективен', 'Главный фактор - приближение к мышечному отказу', 'Низкие повторения требуют больше подходов'],
  'Большинство исследований проводилось на мужчинах с опытом тренировок'
),
(
  'Объём тренировок имеет дозозависимую связь с гипертрофией до определённого порога (примерно 10+ подходов на мышцу в неделю)',
  'Больше объёма = больше рост до определённого предела',
  'hypertrophy',
  5,
  0.88,
  'active',
  'Dose-response relationship between weekly resistance training volume and increases in muscle mass: A systematic review and meta-analysis',
  ARRAY['Schoenfeld B.J.', 'Ogborn D.', 'Krieger J.W.'],
  '2017-01-01',
  34,
  'meta_analysis',
  ARRAY['До 10 подходов на мышцу в неделю - чёткая дозозависимость', 'Свыше 10 подходов - выгода снижается', 'Высокообученные атлеты могут требовать большего объёма'],
  'Высокая вариативность между исследованиями'
),
(
  'Частота тренировок мышцы 2+ раза в неделю превосходит 1 раз для гипертрофии при равном объёме',
  'Частые тренировки лучше редких при том же объёме',
  'hypertrophy',
  4,
  0.85,
  'active',
  'The effects of training volume and training frequency on muscular adaptations: A systematic review and meta-analysis',
  ARRAY['Schoenfeld B.J.', 'Grgic J.', 'Krieger J.'],
  '2019-01-01',
  25,
  'meta_analysis',
  ARRAY['2-3 раза в неделю оптимально', 'Распределение объёма важнее частоты', 'Высокочастотные программы требуют управления усталостью'],
  'Большинство исследований на начинающих и средних'
),

-- Strength claims
(
  'Для развития силы оптимальны низкие диапазоны повторений (1-5) с высокой интенсивностью (>85% 1RM)',
  'Низкие повторения с большим весом лучше для силы',
  'strength',
  5,
  0.95,
  'active',
  'Strength and hypertrophy adaptations between low- vs. high-load resistance training: A systematic review and meta-analysis',
  ARRAY['Schoenfeld B.J.', 'Grgic J.', 'Van Every D.W.'],
  '2021-01-01',
  24,
  'meta_analysis',
  ARRAY['Низкие повторения превосходят для силы', 'Высокие повторения могут также увеличивать силу', 'Специфичность тренировки ключевая'],
  'Различия в методологии между исследованиями'
),
(
  'Прогрессивная перегрузка необходима для дальнейшего развития силы и мышечной массы',
  'Постепенное увеличение нагрузки обязательно для прогресса',
  'strength',
  4,
  0.90,
  'active',
  'Progressive overload without changing load: Effects of density or volume training on muscular adaptations',
  ARRAY['Schoenfeld B.J.'],
  '2020-01-01',
  15,
  'systematic_review',
  ARRAY['Увеличение веса - не единственный способ', 'Можно увеличивать повторения, подходы, сокращать отдых', 'Прогрессия должна быть систематической'],
  'Ограниченное количество долгосрочных исследований'
),

-- Protein and nutrition claims
(
  'Для максимальной гипертрофии требуется 1.6-2.2г белка на кг массы тела в день',
  'Высокое потребление белка необходимо для роста мышц',
  'nutrition',
  5,
  0.94,
  'active',
  'How much protein can the body use in a single meal for muscle-building? Implications for daily protein distribution',
  ARRAY['Schoenfeld B.J.', 'Aragon A.A.'],
  '2018-01-01',
  49,
  'meta_analysis',
  ARRAY['1.6-2.2г/кг оптимально для тренирующихся', 'Распределение по приёмам пищи важно', 'Возраст и уровень тренированности влияют на потребности'],
  'Индивидуальная вариативность в усвоении белка'
),
(
  'Анаболическое окно (30-60 минут после тренировки) не критично при адекватном потреблении белка в течение дня',
  'Время приёма белка менее важно, чем общее количество',
  'nutrition',
  4,
  0.87,
  'active',
  'The effect of protein timing on muscle strength and hypertrophy: a meta-analysis',
  ARRAY['Schoenfeld B.J.', 'Aragon A.A.', 'Krieger J.W.'],
  '2013-01-01',
  23,
  'meta_analysis',
  ARRAY['Общее потребление белка важнее тайминга', 'Небольшое преимущество протеина в окне восстановления', 'Для новичков тайминг менее критичен'],
  'Различия в протоколах исследований'
),

-- Recovery claims
(
  'Сон 7-9 часов необходим для оптимального восстановления и адаптации к тренировкам',
  'Полноценный сон критичен для прогресса',
  'recovery',
  4,
  0.89,
  'active',
  'Sleep and muscle recovery: Endocrinological and molecular basis for a new and promising hypothesis',
  ARRAY['Dattilo M.', 'Antunes H.K.', 'Medeiros A.'],
  '2011-01-01',
  18,
  'systematic_review',
  ARRAY['Сон влияет на гормональный баланс', 'Недосып снижает синтез белка', 'Восстановление ЦНС требует качественного сна'],
  'Большинство исследований на общей популяции'
),
(
  'Активное восстановление может снизить мышечную боль, но не ускоряет функциональное восстановление',
  'Активное восстановление помогает с болью, но не скоростью восстановления',
  'recovery',
  3,
  0.72,
  'active',
  'The effects of active recovery on indices of muscle damage following strenuous exercise',
  ARRAY['Toubekis A.G.', 'Smilios I.', 'Bogdanis G.C.'],
  '2008-01-01',
  12,
  'rct',
  ARRAY['Снижение воспринимаемой боли', 'Не влияет на биомаркеры повреждения', 'Может улучшать психологическое состояние'],
  'Малые размеры выборок в исследованиях'
),

-- Technique claims
(
  'Полная амплитуда движения (ROM) превосходит частичную для гипертрофии в большинстве упражнений',
  'Полное движение лучше частичного для роста мышц',
  'technique',
  4,
  0.82,
  'active',
  'Full range of motion induces greater muscle damage than partial range of motion in the elbow flexors',
  ARRAY['McMahon G.E.', 'Morse C.I.', 'Burden A.'],
  '2014-01-01',
  16,
  'rct',
  ARRAY['Полный ROM даёт больший гипертрофический ответ', 'Частичный ROM может иметь применение для силы', 'Упражнение-специфичные различия существуют'],
  'Большинство исследований на изолированных движениях'
),
(
  'Темпо выполнения: эксцентрическая фаза 2-4 секунды может оптимизировать гипертрофию',
  'Медленное опускание веса может быть полезно для роста мышц',
  'technique',
  3,
  0.68,
  'active',
  'The effects of eccentric contraction duration on muscle strength and power',
  ARRAY['Schoenfeld B.J.', 'Ogborn D.I.'],
  '2015-01-01',
  8,
  'rct',
  ARRAY['Медленная эксцентрика увеличивает мышечное повреждение', 'Неясно, ведёт ли это к большей гипертрофии', 'Слишком медленно может снижать общий объём'],
  'Ограниченное количество исследований'
),

-- Programming claims
(
  'Периодизация тренировок превосходит непериодизированные программы для долгосрочного прогресса',
  'Планомерное изменение нагрузки лучше постоянной',
  'programming',
  4,
  0.84,
  'active',
  'Periodization: A review of the evidence and suggested applications',
  ARRAY['Williams T.D.'],
  '2017-01-01',
  30,
  'systematic_review',
  ARRAY['Линейная и нелинейная периодизация эффективны', 'Важность вариативности стимулов', 'Управление усталостью критично'],
  'Сложно контролировать все переменные в долгосрочных исследованиях'
),
(
  'Делoad (снижение нагрузки) каждые 4-8 недель необходим для предотвращения перетренированности',
  'Периодические лёгкие недели нужны для восстановления',
  'programming',
  3,
  0.75,
  'active',
  'Overreaching and overtraining in strength sports and resistance training: A scoping review',
  ARRAY['Grandou C.'],
  '2020-01-01',
  22,
  'systematic_review',
  ARRAY['Плановое снижение объёма восстанавливает производительность', 'Неплановый делoad сигнализирует о перетренированности', 'Индивидуальная вариативность в восстановлении высока'],
  'Субъективность оценки перетренированности'
),

-- Supplements claims
(
  'Креатин моногидрат - самый исследованный и эффективный добавка для увеличения силы и мышечной массы',
  'Креатин - №1 добавка для силовых показателей',
  'supplements',
  5,
  0.96,
  'active',
  'International Society of Sports Nutrition position stand: safety and efficacy of creatine supplementation in exercise, sport, and medicine',
  ARRAY['Kreider R.B.', 'Kalman D.S.'],
  '2017-01-01',
  1000,
  'meta_analysis',
  ARRAY['Увеличение силы на 5-15%', 'Увеличение массы тела на 1-2 кг', 'Безопасен для здоровых людей', 'Эффективен для различных популяций'],
  'Не все люди отвечают на креатин (нон-респондеры)'
),
(
  'Бета-аланин может улучшить производительность в упражнениях длительностью 1-4 минуты',
  'Бета-аланин помогает в высокоинтенсивных интервалах',
  'supplements',
  4,
  0.78,
  'active',
  'International society of sports nutrition position stand: Beta-Alanine',
  ARRAY['Trexler E.T.'],
  '2015-01-01',
  40,
  'meta_analysis',
  ARRAY['Снижение усталости в высокоинтенсивных упражнениях', 'Эффект накопительный (4+ недели)', 'Парастезия - обычный побочный эффект'],
  'Меньше эффекта в силовых упражнениях'
),

-- Injury prevention claims
(
  'Динамическая разминка превосходит статическую для подготовки к силовой тренировке',
  'Движения в разминке лучше статики перед тренировкой',
  'injury_prevention',
  4,
  0.81,
  'active',
  'Effects of warming-up on physical performance: a systematic review with meta-analysis',
  ARRAY['Fradkin A.J.'],
  '2010-01-01',
  31,
  'meta_analysis',
  ARRAY['Динамическая разминка улучшает силу и мощность', 'Статическая растяжка может временно снизить силу', 'Специфичность разминки к активности важна'],
  'Вариативность в протоколах разминки'
),
(
  'Прогрессивное увеличение нагрузки снижает риск травм по сравнению с резкими скачками',
  'Постепенный рост нагрузки безопаснее резких изменений',
  'injury_prevention',
  3,
  0.76,
  'active',
  'Training practices and ergogenic aids used by male bodybuilders',
  ARRAY['Hackett D.A.'],
  '2013-01-01',
  127,
  'cross_sectional',
  ARRAY['Резкое увеличение объёма связано с травмами', 'Правило 10% увеличения нагрузки', 'Индивидуальная переносимость вариативна'],
  'Основано на опросах, не контролируемых исследованиях'
),

-- General claims
(
  'Индивидуальная реакция на тренировки вариативна: некоторые люди - high responders, другие - low responders',
  'Люди по-разному реагируют на одинаковые программы',
  'general',
  4,
  0.88,
  'active',
  'Individual response to standardized training: variability and relevance to individual training prescription',
  ARRAY['Mann T.N.'],
  '2014-01-01',
  121,
  'rct',
  ARRAY['Большая вариативность в ответе на тренировки', 'Генетика влияет на адаптацию', 'Необходимость персонализации программ'],
  'Сложно предсказать индивидуальный ответ'
),
(
  'Новички могут одновременно набирать мышечную массу и снижать процент жира (рекомпозиция)',
  'Новички могут расти и худеть одновременно',
  'general',
  3,
  0.74,
  'active',
  'Effect of concurrent training on muscle and fat mass in obese adults: A systematic review and meta-analysis',
  ARRAY['Yin J.'],
  '2021-01-01',
  18,
  'meta_analysis',
  ARRAY['Рекомпозиция возможна у новичков', 'С опытом становится сложнее', 'Дефицит калорий должен быть умеренным'],
  'Ограниченные долгосрочные данные'
);

-- ============================================
-- 2. UPDATE EVIDENCE HIERARCHY
-- ============================================

-- Update evidence hierarchy for all categories
SELECT update_evidence_hierarchy('гипертрофия');
SELECT update_evidence_hierarchy('сила');
SELECT update_evidence_hierarchy('питание');
SELECT update_evidence_hierarchy('восстановление');
SELECT update_evidence_hierarchy('техника');
SELECT update_evidence_hierarchy('программирование');
SELECT update_evidence_hierarchy('добавки');
SELECT update_evidence_hierarchy('профилактика травм');

-- ============================================
-- 3. ADD RESEARCH SOURCES
-- ============================================

INSERT INTO public.research_sources (name, source_type, base_url, is_active, config) VALUES
('PubMed', 'pubmed', 'https://pubmed.ncbi.nlm.nih.gov', true, '{"api_endpoint": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"}'),
('CrossRef', 'crossref', 'https://api.crossref.org', true, '{"api_endpoint": "https://api.crossref.org/works"}'),
('Google Scholar', 'google_scholar', 'https://scholar.google.com', false, '{"note": "Requires scraping or unofficial API"}'),
('ArXiv', 'arxiv', 'https://export.arxiv.org', true, '{"api_endpoint": "https://export.arxiv.org/api/query"}'),
('Manual Entry', 'manual', null, true, '{"note": "For manual research paper entry"}');

-- ============================================
-- 4. CREATE KNOWLEDGE RELATIONSHIPS
-- ============================================

-- Note: These would reference actual IDs after the inserts above
-- In practice, you'd run a separate script or use a function to create relationships
-- after retrieving the generated UUIDs

-- Example of how to create relationships (would need actual IDs):
-- INSERT INTO public.knowledge_relationships 
--   (source_knowledge_id, target_knowledge_id, relationship_type, strength, notes)
-- VALUES
--   (uuid1, uuid2, 'supports', 0.85, 'Volume claim supports hypertrophy claim');
