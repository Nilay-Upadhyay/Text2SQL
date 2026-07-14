from __future__ import annotations

from dataclasses import dataclass


TABLE_ALIASES = {
    "payments": "order_payments",
    "reviews": "order_reviews",
    "geolocation": "geolocation",
}

ALL_TABLES = [
    "customers",
    "orders",
    "order_items",
    "products",
    "sellers",
    "geolocation",
    "order_payments",
    "order_reviews",
]

ROLE_ACCESS = {
    "admin": {
        "tables": ALL_TABLES,
        "business_terms": [
            "customers",
            "orders",
            "order_items",
            "products",
            "sellers",
            "geolocation",
            "payments",
            "reviews",
        ],
        "deny_columns": {},
    },
    "sales_analyst": {
        "tables": ["customers", "orders", "order_items", "products", "sellers"],
        "business_terms": ["customers", "orders", "order_items", "products", "sellers"],
        "deny_columns": {
            "customers": [
                "customer_unique_id",
                "customer_zip_code_prefix",
                'customer_city',
                'customer_state',
            ],
            "orders": [],
            "order_items": [],
            "products": [],
            "sellers": [
                "seller_zip_code_prefix",
            ],
        },
    },
    "finance_analyst": {
        "tables": ["customers", "orders", "order_items", "payments"],
        "business_terms": ["customers", "orders", "order_items", "payments"],
        "deny_columns": {
            "customers": ["customer_unique_id",'customer_city', 'customer_state', 'customer_zip_code_prefix'],
            "orders": [],
            "order_items": [],
            "payments": [],
        },
    },
    "customer_support": {
        "tables": ["customers", "orders", "reviews"],
        "business_terms": ["customers", "orders", "reviews"],
        "deny_columns": {
            "customers": [
                "customer_unique_id",
                "customer_zip_code_prefix",
                'customer_city',
                'customer_state',
            ],
            "orders": [],
            "reviews": [],
        },
    },
}


@dataclass(frozen=True)
class SeedAccess:
    user_id: str
    role: str
    tables: tuple[str, ...]
    business_terms: tuple[str, ...]
    deny_columns: dict[str, tuple[str, ...]] = None


def normalize_user_id(user_id: str | None) -> str:
    if not user_id:
        return "admin"
    return "".join(ch if ch.isalnum() else "_" for ch in user_id.strip().lower()).strip("_")


def normalize_table_name(table_name: str) -> str:
    cleaned = table_name.strip().strip('"`')
    return TABLE_ALIASES.get(cleaned.lower(), cleaned)


def get_seed_access(user_id: str | None) -> SeedAccess:
    normalized = normalize_user_id(user_id)
    role = normalized if normalized in ROLE_ACCESS else "admin"
    access = ROLE_ACCESS.get(role, ROLE_ACCESS["admin"])
    return SeedAccess(
        user_id=normalized,
        role=role,
        tables=tuple(access["tables"]),
        business_terms=tuple(access["business_terms"]),
        deny_columns={
            normalize_table_name(table): tuple(cols)
            for table, cols in (access.get("deny_columns") or {}).items()
        },
    )


def get_relationship_tuples(user_id: str | None) -> list[tuple[str, str, str]]:
    access = get_seed_access(user_id)
    role_name = f"role:{access.role}"
    tuples = [
        (f"user:{access.user_id}", "roles", role_name),
        (role_name, "databases", "database:main"),
    ]
    for table_name in access.tables:
        tuples.append((role_name, "tables", f"table:{normalize_table_name(table_name)}"))
    for term_name in access.business_terms:
        tuples.append((role_name, "business_terms", f"business_term:{term_name}"))
    return tuples
