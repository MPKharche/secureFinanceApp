import uuid
from typing import Optional

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.category_group import CategoryGroup
from app.models.rule import Rule
from app.schemas.category import CategoryCreate, CategoryUpdate
from app.services.category_group_service import CATEGORY_TO_GROUP, create_default_groups


class CategoryVisibilityError(ValueError):
    """Raised when visibility is changed for a user-created category."""


# Language-keyed translations for default categories
# Keys are internal identifiers used to map to groups and rules.
# `treat_as_transfer` marks categories whose transactions are flows, not
# income/expense — they're excluded from report aggregations like paired
# transfers are.
DEFAULT_CATEGORIES_I18N = {
    "housing":       {"en": "Housing",         "pt-BR": "Moradia",           "pt-PT": "Habitação",             "de": "Wohnen",             "fr": "Logement",                   "nl": "Wonen",                   "hi": "आवास",              "ta": "வீடு",                "bn": "আবাসন",             "icon": "house",            "color": "#8B5CF6"},
    "food":          {"en": "Food & Dining",   "pt-BR": "Alimentação",       "pt-PT": "Alimentação",           "de": "Essen & Trinken",    "fr": "Alimentation & Restaurants", "nl": "Eten & Drinken",          "hi": "भोजन",              "ta": "உணவு",                "bn": "খাদ্য",              "icon": "utensils-crossed", "color": "#F59E0B"},
    "transport":     {"en": "Transport",       "pt-BR": "Transporte",        "pt-PT": "Transportes",           "de": "Transport",          "fr": "Transport",                  "nl": "Transport",               "hi": "यातायात",           "ta": "போக்குவரத்து",        "bn": "যাতায়াত",           "icon": "car",              "color": "#3B82F6"},
    "groceries":     {"en": "Groceries",       "pt-BR": "Mercado",           "pt-PT": "Supermercado",          "de": "Lebensmittel",       "fr": "Courses",                    "nl": "Boodschappen",            "hi": "किराना",            "ta": "மளிகை",               "bn": "মুদি",               "icon": "shopping-cart",    "color": "#10B981"},
    "health":        {"en": "Health",          "pt-BR": "Saúde",             "pt-PT": "Saúde",                 "de": "Gesundheit",         "fr": "Santé",                      "nl": "Gezondheid",              "hi": "स्वास्थ्य",         "ta": "சுகாதாரம்",            "bn": "স্বাস্থ্য",          "icon": "pill",             "color": "#EF4444"},
    "leisure":       {"en": "Leisure",         "pt-BR": "Lazer",             "pt-PT": "Lazer",                 "de": "Freizeit",           "fr": "Loisirs",                    "nl": "Vrije tijd",              "hi": "मनोरंजन",           "ta": "பொழுதுபோக்கு",         "bn": "অবকাশ",              "icon": "gamepad-2",        "color": "#EC4899"},
    "subscriptions": {"en": "Subscriptions",   "pt-BR": "Assinaturas",       "pt-PT": "Subscrições",           "de": "Abonnements",        "fr": "Abonnements",                "nl": "Abonnementen",            "hi": "सदस्यता",           "ta": "சந்தா",               "bn": "সাবস্ক্রিপশন",       "icon": "smartphone",       "color": "#6366F1"},
    "education":     {"en": "Education",       "pt-BR": "Educação",          "pt-PT": "Educação",              "de": "Bildung",            "fr": "Éducation",                  "nl": "Educatie",                "hi": "शिक्षा",            "ta": "கல்வி",               "bn": "শিক্ষা",             "icon": "book-open",        "color": "#22C55E"},
    "transfers":     {"en": "Transfers",       "pt-BR": "Transferências",    "pt-PT": "Transferências",        "de": "Umbuchungen",        "fr": "Virements",                  "nl": "Overboekingen",           "hi": "स्थानांतरण",        "ta": "பரிமாற்றம்",          "bn": "স্থানান্তর",         "icon": "arrow-left-right", "color": "#64748B", "treat_as_transfer": True},
    "investments":   {"en": "Investments",     "pt-BR": "Investimentos",     "pt-PT": "Investimentos",         "de": "Investitionen",      "fr": "Investissements",            "nl": "Investeringen",           "hi": "निवेश",             "ta": "முதலீடு",             "bn": "বিনিয়োগ",           "icon": "trending-up",      "color": "#0EA5E9", "treat_as_transfer": True},
    "salary":        {"en": "Salary & Income", "pt-BR": "Salário & Renda",   "pt-PT": "Salário & Rendimentos", "de": "Gehalt & Einnahmen", "fr": "Salaire & Revenus",          "nl": "Salaris & Inkomen",       "hi": "वेतन और आय",        "ta": "சம்பளம் மற்றும் வருமானம்", "bn": "বেতন ও আয়",      "icon": "banknote",         "color": "#16A34A"},
    "shopping":      {"en": "Shopping",        "pt-BR": "Compras",           "pt-PT": "Compras",               "de": "Shopping",           "fr": "Achats",                     "nl": "Winkelen",                "hi": "खरीदारी",           "ta": "வாங்குதல்",           "bn": "কেনাকাটা",           "icon": "shopping-bag",     "color": "#F97316"},
    "donations":     {"en": "Donations",       "pt-BR": "Doações",           "pt-PT": "Donativos",             "de": "Spenden",            "fr": "Dons",                       "nl": "Donaties",                "hi": "दान",               "ta": "தானம்",               "bn": "দান",                "icon": "heart-handshake",  "color": "#D946EF"},
    "personal_care": {"en": "Personal Care",   "pt-BR": "Cuidados Pessoais", "pt-PT": "Cuidados Pessoais",     "de": "Körperpflege",       "fr": "Soins personnels",           "nl": "Persoonlijke verzorging", "hi": "व्यक्तिगत देखभाल", "ta": "தனிப்பட்ட பராமரிப்பு", "bn": "ব্যক্তিগত যত্ন",     "icon": "scissors",         "color": "#F472B6"},
    "taxes":         {"en": "Taxes & Fees",    "pt-BR": "Impostos & Taxas",  "pt-PT": "Impostos & Taxas",      "de": "Steuern & Gebühren", "fr": "Impôts & Taxes",             "nl": "Belastingen & Heffingen", "hi": "कर और शुल्क",       "ta": "வரி மற்றும் கட்டணம்",  "bn": "কর ও ফি",            "icon": "landmark",         "color": "#78716C"},
    # Indian-specific categories
    "house_help":    {"en": "House Help",      "pt-BR": "Empregados Domésticos", "pt-PT": "Empregados Domésticos", "de": "Haushaltshilfe",  "fr": "Aide domestique",           "nl": "Huishoudelijk personeel", "hi": "घरेलू सहायता",      "ta": "வீட்டு உதவியாளர்",     "bn": "গৃহকর্মী",           "icon": "users",            "color": "#EC4899"},
    "tuition":       {"en": "Tuition & Coaching", "pt-BR": "Aulas Particulares", "pt-PT": "Explicações",        "de": "Nachhilfe",          "fr": "Cours particuliers",        "nl": "Bijles",                  "hi": "ट्यूशन और कोचिंग",  "ta": "பயிற்சி வகுப்புகள்",  "bn": "টিউশন ও কোচিং",     "icon": "graduation-cap",   "color": "#6366F1"},
    "school_fees":   {"en": "School Fees",     "pt-BR": "Mensalidades Escolares", "pt-PT": "Propinas Escolares", "de": "Schulgebühren",     "fr": "Frais de scolarité",        "nl": "Schoolgeld",              "hi": "स्कूल शुल्क",       "ta": "பள்ளி கட்டணம்",       "bn": "স্কুল ফি",           "icon": "school",           "color": "#10B981"},
    "medical":       {"en": "Medical & Doctors", "pt-BR": "Médicos",           "pt-PT": "Médicos",               "de": "Ärzte",              "fr": "Médecins",                  "nl": "Artsen",                  "hi": "चिकित्सा और डॉक्टर", "ta": "மருத்துவம்",          "bn": "চিকিৎসা",            "icon": "stethoscope",      "color": "#EF4444"},
    "insurance":     {"en": "Insurance Premium", "pt-BR": "Seguro",           "pt-PT": "Seguro",                "de": "Versicherung",       "fr": "Assurance",                 "nl": "Verzekering",             "hi": "बीमा प्रीमियम",     "ta": "காப்பீட்டு பிரீமியம்", "bn": "বীমা প্রিমিয়াম",    "icon": "shield",           "color": "#3B82F6"},
    "gold":          {"en": "Gold & Jewelry",  "pt-BR": "Ouro e Joias",      "pt-PT": "Ouro e Joalharia",      "de": "Gold & Schmuck",     "fr": "Or et bijoux",              "nl": "Goud & sieraden",         "hi": "सोना और आभूषण",    "ta": "தங்கம் மற்றும் நகைகள்", "bn": "স্বর্ণ ও গহনা",    "icon": "gem",              "color": "#F59E0B"},
    "religious":     {"en": "Religious & Donations", "pt-BR": "Doações Religiosas", "pt-PT": "Donativos Religiosos", "de": "Religiöse Spenden", "fr": "Dons religieux",         "nl": "Religieuze donaties",     "hi": "धार्मिक और दान",    "ta": "மத நன்கொடை",         "bn": "ধর্মীয় দান",         "icon": "church",           "color": "#D946EF"},
    "festivals":     {"en": "Festivals & Events", "pt-BR": "Festas e Eventos", "pt-PT": "Festas e Eventos",     "de": "Feste & Events",     "fr": "Fêtes et événements",       "nl": "Feesten & evenementen",   "hi": "त्यौहार और कार्यक्रम", "ta": "பண்டிகைகள்",       "bn": "উৎসব ও অনুষ্ঠান",     "icon": "party-popper",     "color": "#EC4899"},
    "pet_care":      {"en": "Pet Care",        "pt-BR": "Cuidados com Animais", "pt-PT": "Cuidados com Animais", "de": "Haustierpflege",    "fr": "Soins pour animaux",        "nl": "Huisdierverzorging",      "hi": "पालतू जानवर देखभाल", "ta": "செல்லப்பிராணி பராமரிப்பு", "bn": "পোষা প্রাণী যত্ন", "icon": "dog",           "color": "#F97316"},
    "tobacco_alcohol": {"en": "Tobacco & Alcohol", "pt-BR": "Tabaco e Álcool", "pt-PT": "Tabaco e Álcool",     "de": "Tabak & Alkohol",    "fr": "Tabac et alcool",           "nl": "Tabak & alcohol",         "hi": "तंबाकू और शराब",    "ta": "புகையிலை மற்றும் மது", "bn": "তামাক ও মদ",        "icon": "cigarette",        "color": "#78716C"},
    "other":         {"en": "Other",           "pt-BR": "Outros",            "pt-PT": "Outros",                "de": "Sonstiges",          "fr": "Autres",                     "nl": "Overig",                  "hi": "अन्य",              "ta": "மற்றவை",             "bn": "অন্যান্য",           "icon": "circle-help",      "color": "#6B7280"},
}


async def create_default_categories(
    session: AsyncSession,
    user_id: uuid.UUID,
    lang: str = "pt-BR",
    workspace_id: Optional[uuid.UUID] = None,
) -> list[Category]:
    # Guard against double-creation. Scope the check to the workspace
    # when one is provided so a user creating a SECOND workspace still
    # gets the defaults seeded there — the prior guard checked
    # user_id and short-circuited every workspace after the first.
    if workspace_id is not None:
        existing = await session.execute(
            select(Category).where(Category.workspace_id == workspace_id).limit(1)
        )
        if existing.scalar_one_or_none():
            return await get_categories(session, workspace_id)
    else:
        # Legacy/test path with no explicit workspace_id — fall back to
        # the user's first workspace via the autostamp listener.
        existing = await session.execute(
            select(Category).where(Category.user_id == user_id).limit(1)
        )
        if existing.scalar_one_or_none():
            from app.models.workspace import Workspace, WorkspaceMember
            row = await session.execute(
                select(Workspace.id)
                .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
                .where(WorkspaceMember.user_id == user_id)
                .limit(1)
            )
            scope_id = row.scalar()
            return await get_categories(session, scope_id) if scope_id else []

    # Create default groups first
    groups = await create_default_groups(session, user_id, lang, workspace_id=workspace_id)

    categories = []
    for key, data in DEFAULT_CATEGORIES_I18N.items():
        name = data.get(lang, data.get("en", key))
        group_key = CATEGORY_TO_GROUP.get(key)
        group = groups.get(group_key) if group_key else None
        category = Category(
            user_id=user_id,
            workspace_id=workspace_id,
            name=name,
            icon=data["icon"],
            color=data["color"],
            is_system=True,
            group_id=group.id if group else None,
            treat_as_transfer=data.get("treat_as_transfer", False),
        )
        session.add(category)
        categories.append(category)
    await session.commit()
    return categories


async def get_hidden_category_ids(
    session: AsyncSession, workspace_id: uuid.UUID
) -> set[uuid.UUID]:
    """Ids of categories the workspace hides, directly or through their group.

    The rule engine needs these so it never files a transaction under a
    category the user has taken out of circulation.
    """
    result = await session.execute(
        select(Category.id)
        .outerjoin(CategoryGroup, Category.group_id == CategoryGroup.id)
        .where(
            Category.workspace_id == workspace_id,
            or_(Category.is_hidden.is_(True), CategoryGroup.is_hidden.is_(True)),
        )
    )
    return set(result.scalars().all())


async def get_categories(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    *,
    include_hidden: bool = False,
) -> list[Category]:
    filters = [Category.workspace_id == workspace_id]
    if not include_hidden:
        filters.append(Category.is_hidden.is_(False))
        filters.append(or_(Category.group_id.is_(None), CategoryGroup.is_hidden.is_(False)))

    result = await session.execute(
        select(Category)
        .outerjoin(CategoryGroup, Category.group_id == CategoryGroup.id)
        .where(*filters)
        .order_by(Category.is_hidden.asc(), Category.is_system.desc(), Category.name)
    )
    return list(result.scalars().all())


async def get_category(
    session: AsyncSession, category_id: uuid.UUID, workspace_id: uuid.UUID
) -> Optional[Category]:
    result = await session.execute(
        select(Category).where(
            Category.id == category_id, Category.workspace_id == workspace_id
        )
    )
    return result.scalar_one_or_none()


async def create_category(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    data: CategoryCreate,
) -> Category:
    category = Category(user_id=user_id, workspace_id=workspace_id, **data.model_dump())
    session.add(category)
    await session.commit()
    await session.refresh(category)
    return category


async def get_rules_assigning_category(
    session: AsyncSession, workspace_id: uuid.UUID, category_id: uuid.UUID
) -> list[Rule]:
    """Active rules whose `set_category` action targets this category.

    Hiding a category is how a user retires it, but a rule that assigns it
    keeps categorizing new transactions into it. The UI lists these so the
    user can retire the rules in the same step.
    """
    result = await session.execute(
        select(Rule)
        .where(Rule.workspace_id == workspace_id, Rule.is_active.is_(True))
        .order_by(Rule.priority, Rule.id)
    )
    target = str(category_id)
    return [
        rule
        for rule in result.scalars().all()
        if any(
            action.get("op") == "set_category" and str(action.get("value")) == target
            for action in (rule.actions or [])
        )
    ]


async def deactivate_rules_assigning_category(
    session: AsyncSession, workspace_id: uuid.UUID, category_id: uuid.UUID
) -> int:
    """Turn off the rules that assign this category and report how many."""
    rules = await get_rules_assigning_category(session, workspace_id, category_id)
    for rule in rules:
        rule.is_active = False
    return len(rules)


async def update_category(
    session: AsyncSession,
    category_id: uuid.UUID,
    workspace_id: uuid.UUID,
    data: CategoryUpdate,
    *,
    deactivate_rules: bool = False,
) -> Optional[Category]:
    """Update a category, optionally retiring the rules that assign it.

    `deactivate_rules` only applies when the category is being hidden: the
    rules that filed transactions under it would otherwise stay listed as
    active while the engine skips their categorization.
    """
    category = await get_category(session, category_id, workspace_id)
    if not category:
        return None

    changes = data.model_dump(exclude_unset=True)
    if changes.get("is_hidden") is True and not category.is_system:
        raise CategoryVisibilityError("Only system categories can be hidden")

    for key, value in changes.items():
        setattr(category, key, value)

    if deactivate_rules and changes.get("is_hidden") is True:
        await deactivate_rules_assigning_category(session, workspace_id, category_id)

    await session.commit()
    await session.refresh(category)
    return category


async def delete_category(
    session: AsyncSession, category_id: uuid.UUID, workspace_id: uuid.UUID
) -> bool:
    category = await get_category(session, category_id, workspace_id)
    if not category or category.is_system:
        return False

    try:
        await session.delete(category)
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ValueError(
            "Category is still in use and cannot be deleted. Remove its references first."
        ) from exc
    return True
