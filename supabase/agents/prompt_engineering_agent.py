"""
Prompt Engineering Agent (📝) - Генерация системных промптов для AI Coach

Отвечает за:
- Анализ knowledge base по категориям
- Генерацию контекстно-зависимых системных промптов
- Версионирование промптов
- A/B тестирование промптов
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import json

from agents.base_agent import BaseAgent
from services.supabase_client import SupabaseClient, PromptVersion


@dataclass
class KnowledgeSummary:
    """Сводка знаний по категории."""
    category: str
    total_claims: int
    avg_evidence_level: float
    avg_confidence: float
    top_claims: List[Dict[str, Any]]
    conflicting_areas: List[str]
    knowledge_gaps: List[str]


class PromptEngineeringAgent(BaseAgent):
    """
    Agent для генерации системных промптов на основе научных данных.
    
    Генерирует промпты для разных категорий:
    - strength_training (силовые тренировки)
    - hypertrophy (гипертрофия)
    - nutrition (питание)
    - recovery (восстановление)
    - cardio (кардио)
    - general (общие рекомендации)
    """
    
    # Шаблоны промптов для разных категорий
    PROMPT_TEMPLATES = {
        'strength_training': """You are an expert strength training coach with deep knowledge of exercise science.

Your responses must be based on the following scientific evidence:

{evidence_section}

Guidelines:
1. Always cite the evidence level (1-5) for each claim
2. Distinguish between established facts and emerging research
3. Acknowledge when evidence is conflicting or limited
4. Provide practical, actionable advice
5. Consider individual differences (training age, genetics, injury history)

When evidence is insufficient, say so clearly and explain why.
""",
        'hypertrophy': """You are an expert in muscle hypertrophy and body composition.

Scientific foundation:
{evidence_section}

Response guidelines:
1. Reference specific studies when making claims
2. Explain mechanisms (mTOR, muscle protein synthesis, etc.)
3. Distinguish between trained and untrained individuals
4. Address common myths with evidence
5. Provide periodization recommendations
""",
        'nutrition': """You are a sports nutrition specialist.

Evidence base:
{evidence_section}

Key principles:
1. Base recommendations on peer-reviewed research
2. Consider total caloric context
3. Address nutrient timing when relevant
4. Distinguish between optimal and adequate intake
5. Note individual variability in response
""",
        'recovery': """You are a recovery and regeneration specialist.

Scientific basis:
{evidence_section}

Approach:
1. Emphasize evidence-based recovery modalities
2. Distinguish between active and passive recovery
3. Address sleep, stress, and lifestyle factors
4. Consider training load context
5. Acknowledge limitations in recovery research
""",
        'cardio': """You are a cardiovascular training specialist.

Evidence base:
{evidence_section}

Guidelines:
1. Reference heart rate zones and training intensities
2. Distinguish between aerobic and anaerobic training
3. Consider individual fitness levels
4. Address VO2max and endurance adaptations
5. Provide progressive overload recommendations
""",
        'general': """You are an AI fitness coach powered by scientific research.

Current knowledge base:
{evidence_section}

Core principles:
1. Prioritize safety and long-term health
2. Base recommendations on scientific consensus
3. Acknowledge uncertainty when appropriate
4. Encourage progressive overload
5. Emphasize consistency over perfection
"""
    }
    
    def __init__(
        self,
        supabase: SupabaseClient,
        llm_service: Optional[Any] = None,
        categories: Optional[List[str]] = None
    ):
        super().__init__(name="PromptEngineeringAgent", supabase=supabase)
        self.llm = llm_service
        self.categories = categories or list(self.PROMPT_TEMPLATES.keys())
        self.stats['prompts_generated'] = 0
        self.stats['prompts_activated'] = 0
    
    async def process(self) -> Dict[str, Any]:
        """
        Главный метод: анализирует KB и генерирует/обновляет промпты.
        
        Returns:
            Результаты генерации промптов
        """
        results = {
            'categories_processed': 0,
            'prompts_generated': 0,
            'prompts_activated': 0,
            'errors': []
        }
        
        for category in self.categories:
            try:
                # 1. Анализируем knowledge base
                summary = await self._analyze_knowledge(category)
                
                # 2. Проверяем нужно ли обновление
                if await self._should_update_prompt(category, summary):
                    # 3. Генерируем новый промпт
                    prompt = await self._generate_prompt(category, summary)
                    
                    # 4. Валидируем промпт
                    if await self._validate_prompt(prompt):
                        # 5. Сохраняем версию
                        version = await self._save_prompt_version(category, prompt, summary)
                        
                        # 6. Активируем если нужно
                        if await self._should_activate(version):
                            await self._activate_prompt(version)
                            results['prompts_activated'] += 1
                        
                        results['prompts_generated'] += 1
                
                results['categories_processed'] += 1
                
            except Exception as e:
                self.logger.error(f"Error processing category {category}: {e}")
                results['errors'].append({'category': category, 'error': str(e)})
        
        self.stats['prompts_generated'] += results['prompts_generated']
        self.stats['prompts_activated'] += results['prompts_activated']
        
        return results
    
    async def _analyze_knowledge(self, category: str) -> KnowledgeSummary:
        """
        Анализирует knowledge base для категории.
        
        Args:
            category: Категория знаний
            
        Returns:
            Сводка знаний
        """
        # Получаем claims из БД
        claims = await self.supabase.get_claims_by_category_with_filters(
            category=category,
            min_evidence_level=2,
            min_confidence=0.7,
            limit=50
        )
        
        if not claims:
            return KnowledgeSummary(
                category=category,
                total_claims=0,
                avg_evidence_level=0,
                avg_confidence=0,
                top_claims=[],
                conflicting_areas=[],
                knowledge_gaps=[]
            )
        
        # Анализируем статистику
        evidence_levels = [c.evidence_level for c in claims]
        confidences = [c.confidence_score for c in claims]
        
        # Находим топ claims
        top_claims = sorted(
            claims,
            key=lambda c: (c.evidence_level, c.confidence_score),
            reverse=True
        )[:10]
        
        # Ищем конфликты
        conflicting = await self._find_conflicting_claims(category, claims)
        
        # Ищем пробелы в знаниях
        gaps = self._identify_knowledge_gaps(category, claims)
        
        return KnowledgeSummary(
            category=category,
            total_claims=len(claims),
            avg_evidence_level=sum(evidence_levels) / len(evidence_levels),
            avg_confidence=sum(confidences) / len(confidences),
            top_claims=[self._claim_to_dict(c) for c in top_claims],
            conflicting_areas=conflicting,
            knowledge_gaps=gaps
        )
    
    async def _should_update_prompt(
        self,
        category: str,
        summary: KnowledgeSummary
    ) -> bool:
        """
        Определяет нужно ли обновлять промпт.
        
        Args:
            category: Категория
            summary: Текущая сводка знаний
            
        Returns:
            True если нужно обновление
        """
        # Получаем текущий активный промпт
        current = await self.supabase.get_active_prompt(category)
        
        if not current:
            return True
        
        # Проверяем существенные изменения
        snapshot = current.knowledge_snapshot
        
        # Много новых claims
        if summary.total_claims > snapshot.get('total_claims', 0) * 1.2:
            return True
        
        # Изменилось среднее качество evidence
        if abs(summary.avg_evidence_level - snapshot.get('avg_evidence_level', 0)) > 0.5:
            return True
        
        # Появились новые конфликты
        if len(summary.conflicting_areas) > len(snapshot.get('conflicting_areas', [])):
            return True
        
        # Промпт старый (больше недели)
        if current.created_at:
            age = datetime.now() - current.created_at
            if age.days > 7:
                return True
        
        return False
    
    async def _generate_prompt(
        self,
        category: str,
        summary: KnowledgeSummary
    ) -> str:
        """
        Генерирует системный промпт.
        
        Args:
            category: Категория
            summary: Сводка знаний
            
        Returns:
            Текст промпта
        """
        # Формируем секцию с evidence
        evidence_section = self._format_evidence_section(summary)
        
        # Получаем базовый шаблон
        template = self.PROMPT_TEMPLATES.get(
            category,
            self.PROMPT_TEMPLATES['general']
        )
        
        # Вставляем evidence
        prompt = template.format(evidence_section=evidence_section)
        
        # Добавляем информацию о конфликтах если есть
        if summary.conflicting_areas:
            conflict_section = self._format_conflict_section(summary.conflicting_areas)
            prompt += f"\n\nAreas of Active Research/Debate:\n{conflict_section}"
        
        # Добавляем пробелы в знаниях
        if summary.knowledge_gaps:
            gaps_section = self._format_gaps_section(summary.knowledge_gaps)
            prompt += f"\n\nCurrent Knowledge Limitations:\n{gaps_section}"
        
        return prompt
    
    def _format_evidence_section(self, summary: KnowledgeSummary) -> str:
        """Форматирует секцию с evidence."""
        lines = [
            f"Total scientific claims: {summary.total_claims}",
            f"Average evidence level: {summary.avg_evidence_level:.1f}/5",
            f"Average confidence: {summary.avg_confidence:.1%}",
            "",
            "Key findings (highest evidence):",
        ]
        
        for i, claim in enumerate(summary.top_claims[:5], 1):
            lines.append(
                f"{i}. [{claim['evidence_level']}/5] {claim['claim']} "
                f"(confidence: {claim['confidence']:.0%})"
            )
        
        return '\n'.join(lines)
    
    async def _validate_prompt(self, prompt: str) -> bool:
        """
        Валидирует сгенерированный промпт.
        
        Args:
            prompt: Текст промпта
            
        Returns:
            True если промпт валиден
        """
        # Проверяем длину
        if len(prompt) < 100:
            self.logger.warning("Prompt too short")
            return False
        
        if len(prompt) > 8000:
            self.logger.warning("Prompt too long")
            return False
        
        # Проверяем наличие ключевых секций
        required_sections = [
            'evidence',
            'scientific',
        ]
        
        prompt_lower = prompt.lower()
        for section in required_sections:
            if section not in prompt_lower:
                self.logger.warning(f"Missing section: {section}")
                return False
        
        # Если есть LLM service, можно сделать дополнительную валидацию
        if self.llm:
            # TODO: Добавить LLM-based валидацию
            pass
        
        return True
    
    async def _save_prompt_version(
        self,
        category: str,
        prompt: str,
        summary: KnowledgeSummary
    ) -> PromptVersion:
        """Сохраняет новую версию промпта."""
        # Получаем следующую версию
        latest = await self.supabase.get_latest_prompt_version(category)
        version_num = (latest.version + 1) if latest else 1
        
        prompt_version = PromptVersion(
            id=None,
            category=category,
            prompt_text=prompt,
            version=version_num,
            knowledge_snapshot={
                'total_claims': summary.total_claims,
                'avg_evidence_level': summary.avg_evidence_level,
                'avg_confidence': summary.avg_confidence,
                'conflicting_areas': summary.conflicting_areas,
                'generated_at': datetime.now().isoformat()
            },
            performance_score=None,
            is_active=False,
            created_at=None,
            metadata={
                'generator_version': '1.0',
                'template_used': category
            }
        )
        
        # Сохраняем в БД
        saved = await self.supabase.save_prompt_version(prompt_version)
        return saved
    
    async def _should_activate(self, version: PromptVersion) -> bool:
        """Определяет нужно ли активировать новую версию."""
        # Если это первая версия - активируем
        if version.version == 1:
            return True
        
        # Если нет активного промпта - активируем
        current = await self.supabase.get_active_prompt(version.category)
        if not current:
            return True
        
        # TODO: Добавить A/B тестирование логику
        # Пока активируем если версия новая
        return version.version > current.version
    
    async def _activate_prompt(self, version: PromptVersion):
        """Активирует версию промпта."""
        await self.supabase.activate_prompt_version(version.id)
        self.logger.info(f"Activated prompt version {version.version} for {version.category}")
    
    async def _find_conflicting_claims(
        self,
        category: str,
        claims: List[Any]
    ) -> List[str]:
        """Находит области с конфликтующими claims."""
        # TODO: Реализовать semantic similarity поиск
        # Пока заглушка
        return []
    
    def _identify_knowledge_gaps(
        self,
        category: str,
        claims: List[Any]
    ) -> List[str]:
        """Идентифицирует пробелы в знаниях."""
        gaps = []
        
        # Проверяем минимальное количество claims
        if len(claims) < 10:
            gaps.append(f"Limited research available ({len(claims)} claims)")
        
        # Проверяем средний уровень evidence
        avg_evidence = sum(c.evidence_level for c in claims) / len(claims) if claims else 0
        if avg_evidence < 3:
            gaps.append("Most evidence is from lower-quality studies")
        
        return gaps
    
    def _claim_to_dict(self, claim: Any) -> Dict[str, Any]:
        """Конвертирует claim в словарь."""
        return {
            'id': claim.id,
            'claim': claim.claim,
            'evidence_level': claim.evidence_level,
            'confidence': claim.confidence_score,
            'category': claim.category
        }
    
    def _format_conflict_section(self, conflicts: List[str]) -> str:
        """Форматирует секцию конфликтов."""
        return '\n'.join(f"- {c}" for c in conflicts)
    
    def _format_gaps_section(self, gaps: List[str]) -> str:
        """Форматирует секцию пробелов."""
        return '\n'.join(f"- {g}" for g in gaps)
