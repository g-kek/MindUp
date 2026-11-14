"""Authored practice questions on topics documented by IELTS co-owners.

These are adaptations for practice, not predictions or verbatim official exam questions.
Automatic selection deliberately receives no interests, occupation or personal memories.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from mindup_bot.ai.schemas import TopicChoice


@dataclass(frozen=True)
class ExamTopic:
    slug: str
    title: str
    title_ru: str
    aliases: tuple[str, ...]
    source_url: str
    source_label: str
    opening: str
    second: str
    cue: str
    discussion: tuple[str, str]

    def choice(self) -> TopicChoice:
        return TopicChoice(
            topic_id=f"ielts_{self.slug}",
            title=self.title,
            opening_question=self.opening,
            rationale="Topic documented in IELTS preparation materials; questions adapted for practice.",
            practice_mode="ielts",
            second_question=self.second,
            cue_card=self.cue,
            discussion_questions=list(self.discussion),
            source_url=self.source_url,
            source_label=self.source_label,
        )


TOPICS = (
    ExamTopic(
        "home",
        "Hometown and housing",
        "Родной город и жильё",
        ("home", "hometown", "housing", "accommodation", "дом", "жильё", "жилье", "город"),
        "https://takeielts.britishcouncil.org/what-is-ielts/how-it-works/test-format/speaking",
        "British Council · Speaking topics",
        "Which features of the area where you grew up stand out to you?",
        "How does your current home compare with the home you would like in the future?",
        "Describe a home you remember particularly well.\nYou should say:\n"
        "• where it was\n• who lived there\n• what it looked like\nand explain what made it memorable.",
        (
            "What should planners prioritise when building residential areas?",
            "Why do housing needs differ between younger and older people?",
        ),
    ),
    ExamTopic(
        "work_study",
        "Work and studies",
        "Работа и учёба",
        ("work", "study", "studies", "education", "работа", "учёба", "учеба", "образование"),
        "https://takeielts.britishcouncil.org/prepare/ielts-academic/speaking",
        "British Council · Academic Speaking preparation",
        "What led you to your current work or course of study?",
        "Which part of your working or studying day requires the most effort?",
        "Describe a skill you acquired through work or study.\nYou should say:\n"
        "• what the skill was\n• how you learnt it\n• where you used it\nand explain why it mattered.",
        (
            "How should education prepare people for changing careers?",
            "What responsibilities do employers have for helping staff learn?",
        ),
    ),
    ExamTopic(
        "friends",
        "Friends and relationships",
        "Друзья и общение",
        ("friends", "friendship", "relationships", "друзья", "дружба", "общение"),
        "https://ielts.idp.com/prepare/article-ielts-speaking-test-part-1",
        "IDP IELTS · Part 1: friends",
        "What do you and your friends tend to do when you meet?",
        "How has the way you keep in touch with friends changed as you have grown older?",
        "Describe an occasion when a friend helped you.\nYou should say:\n"
        "• what the situation was\n• what your friend did\n• what happened afterwards\n"
        "and explain how the experience affected your friendship.",
        (
            "What can make friendships between different generations valuable?",
            "How has online communication changed the way people maintain friendships?",
        ),
    ),
    ExamTopic(
        "food",
        "Food and cooking",
        "Еда и приготовление пищи",
        ("food", "cooking", "meals", "еда", "кулинария", "готовка"),
        "https://ielts.idp.com/prepare/article-how-to-talk-naturally-about-food-in-ielts-speaking",
        "IDP IELTS · Food across Speaking Parts 1–3",
        "How much of your weekly food do you prepare yourself?",
        "Which eating habits in your family have changed over time?",
        "Describe a meal that you associate with a special occasion.\nYou should say:\n"
        "• what was served\n• who shared the meal\n• where it took place\nand explain why you remember it.",
        (
            "Why do food traditions remain important when lifestyles change?",
            "How might international food businesses affect local eating habits?",
        ),
    ),
    ExamTopic(
        "hobbies",
        "Hobbies and free time",
        "Увлечения и свободное время",
        ("hobbies", "hobby", "leisure", "free time", "хобби", "увлечения", "свободное время"),
        "https://ielts.idp.com/vietnam/about/news-and-articles/article-talk-about-your-hobby/en-gb",
        "IDP IELTS · Hobby topic guide",
        "Which activity do you make time for outside work or study?",
        "What first encouraged you to try that activity?",
        "Describe a leisure activity you have kept doing for some time.\nYou should say:\n"
        "• how you began\n• when you do it\n• what you need for it\nand explain why you continue.",
        (
            "What makes some leisure activities appeal to several generations?",
            "How can communities make leisure activities accessible to more people?",
        ),
    ),
    ExamTopic(
        "travel",
        "Holidays and travel",
        "Отпуск и путешествия",
        ("travel", "holidays", "holiday", "tourism", "путешествия", "отпуск", "туризм"),
        "https://ielts.idp.com/bangladesh/about/news-and-articles/article-common-ielts-speaking-topics",
        "IDP IELTS · Speaking sample topics",
        "When you take a break, do you tend to explore somewhere new or revisit a familiar place?",
        "What influences your choice of holiday destination?",
        "Describe a trip that left a lasting impression on you.\nYou should say:\n"
        "• where you travelled\n• who accompanied you\n• what you did there\nand explain what stayed in your memory.",
        (
            "What can visitors do to reduce the negative effects of tourism?",
            "How might travelling abroad change a person's understanding of other cultures?",
        ),
    ),
    ExamTopic(
        "music_films",
        "Music and films",
        "Музыка и фильмы",
        ("music", "films", "movies", "cinema", "музыка", "фильмы", "кино"),
        "https://ielts.idp.com/prepare/article-free-speaking-practice-questions",
        "IDP IELTS · Speaking practice questions",
        "What sort of music or films do you return to most often?",
        "How have your entertainment choices changed since you were younger?",
        "Describe a film or musical performance that made an impression on you.\nYou should say:\n"
        "• what it was\n• when you encountered it\n• what you remember about it\nand explain its effect on you.",
        (
            "How do streaming services influence people's cultural choices?",
            "What role can music and film play in preserving a culture?",
        ),
    ),
    ExamTopic(
        "sports",
        "Sport and physical activity",
        "Спорт и физическая активность",
        ("sport", "sports", "exercise", "спорт", "физическая активность"),
        "https://takeielts.britishcouncil.org/sites/default/files/speaking_part_1_grammatical_range_and_accuracy_lexical_resource.pdf",
        "British Council · Speaking practice worksheet",
        "What kinds of physical activity fit into your normal week?",
        "How does the sport you enjoy now compare with what you enjoyed as a child?",
        "Describe a sporting activity you tried or watched.\nYou should say:\n"
        "• what the activity was\n• where it took place\n• who was involved\nand explain what you learnt from it.",
        (
            "How can local authorities encourage people to be physically active?",
            "What are the benefits and drawbacks of competitive sport for children?",
        ),
    ),
    ExamTopic(
        "possessions",
        "Possessions, values and advertising",
        "Вещи, ценности и реклама",
        (
            "possessions",
            "shopping",
            "advertising",
            "values",
            "вещи",
            "покупки",
            "реклама",
            "ценности",
        ),
        "https://takeielts.britishcouncil.org/sites/default/files/%5Bdownloads%5D/ielts-speaking-sample-tasks-2023.pdf",
        "IELTS.org / British Council · Official sample tasks",
        "Do you tend to keep possessions for many years or replace them regularly?",
        "How do you decide whether an item is worth buying?",
        "Describe an object that has particular personal value for you.\nYou should say:\n"
        "• how it came into your life\n• how you use or keep it\n• what it reminds you of\n"
        "and explain why you value it.",
        (
            "Why can certain possessions become symbols of social status?",
            "How does advertising influence the things that people consider necessary?",
        ),
    ),
    ExamTopic(
        "weather",
        "Weather and daily life",
        "Погода и повседневная жизнь",
        ("weather", "climate", "seasons", "погода", "климат", "времена года"),
        "https://ielts.idp.com/nepal/prepare/speaking/part-1-topics-and-questions",
        "IDP IELTS · Speaking topic bank",
        "How does the weather affect the way you spend your day?",
        "Which season is easiest for you to plan outdoor activities in, and why?",
        "Describe an occasion when weather changed your plans.\nYou should say:\n"
        "• what you had planned\n• what the weather was like\n• what you did instead\nand explain how you felt.",
        (
            "How should towns prepare for increasingly unpredictable weather?",
            "Why might people in different occupations experience weather changes differently?",
        ),
    ),
)


class UnknownIELTSTopic(ValueError):
    pass


def choose_exam_topic(recent_topics: list[dict[str, Any]]) -> TopicChoice:
    recent_ids = {item.get("topic_id") for item in recent_topics}
    recent_titles = {item.get("title") for item in recent_topics}
    for topic in TOPICS:
        if f"ielts_{topic.slug}" not in recent_ids and topic.title not in recent_titles:
            return topic.choice()
    # History is newest first. An old occurrence must not hide a recent repeat.
    last_seen: dict[str, int] = {}
    for index, item in enumerate(recent_topics):
        for topic in TOPICS:
            if item.get("topic_id") == f"ielts_{topic.slug}" or item.get("title") == topic.title:
                last_seen.setdefault(topic.slug, index)
    return max(TOPICS, key=lambda topic: last_seen.get(topic.slug, -1)).choice()


def requested_exam_topic(request: str) -> TopicChoice:
    normalized = request.strip().casefold()
    if normalized.isdecimal() and 1 <= int(normalized) <= len(TOPICS):
        return TOPICS[int(normalized) - 1].choice()
    matches = [
        topic
        for topic in TOPICS
        if any(
            re.search(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", normalized)
            for alias in (*topic.aliases, topic.title.casefold(), topic.title_ru.casefold())
        )
    ]
    if len(matches) == 1:
        return matches[0].choice()
    raise UnknownIELTSTopic(request)


def exam_topics_menu(language: str | None) -> str:
    return "\n".join(
        f"{index}. {topic.title if language == 'en' else topic.title_ru}"
        for index, topic in enumerate(TOPICS, 1)
    )
