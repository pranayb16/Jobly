JOB_FAMILIES = [
    "software_engineering",
    "data_engineering",
    "data_science",
    "data_analytics",
    "machine_learning",
    "devops_sre",
    "cybersecurity",
    "qa_testing",
    "product_management",
    "project_management",
    "design",
    "sales",
    "marketing",
    "finance",
    "hr_recruiting",
    "customer_support",
    "customer_success",
    "operations",
    "other",
]


SUBFAMILIES_BY_FAMILY = {
    "software_engineering": [
        "backend_engineering",
        "frontend_engineering",
        "full_stack_engineering",
        "mobile_engineering",
        "platform_engineering",
        "embedded_engineering",
        "general_software_engineering",
    ],

    "data_engineering": [
        "data_platform",
        "analytics_engineering",
        "etl_data_pipeline",
        "general_data_engineering",
    ],

    "data_science": [
        "general_data_science",
        "applied_data_science",
        "research_data_science",
    ],

    "data_analytics": [
        "business_intelligence",
        "business_analytics",
        "product_analytics",
        "general_data_analytics",
    ],

    "machine_learning": [
        "ml_engineering",
        "applied_machine_learning",
        "ml_platform",
        "ai_research",
    ],

    "devops_sre": [
        "devops_engineering",
        "site_reliability_engineering",
        "cloud_infrastructure",
        "infrastructure_engineering",
    ],

    "cybersecurity": [
        "security_engineering",
        "application_security",
        "security_operations",
        "cloud_security",
        "governance_risk_compliance",
    ],

    "qa_testing": [
        "manual_testing",
        "test_automation",
        "quality_engineering",
    ],

    "product_management": [
        "general_product_management",
        "technical_product_management",
        "growth_product_management",
    ],

    "project_management": [
        "project_management",
        "program_management",
        "technical_program_management",
    ],

    "design": [
        "product_design",
        "ux_design",
        "ui_design",
        "graphic_design",
    ],

    "sales": [
        "account_executive",
        "sales_development",
        "business_development",
        "sales_engineering",
        "account_management",
    ],

    "marketing": [
        "product_marketing",
        "growth_marketing",
        "content_marketing",
        "demand_generation",
        "performance_marketing",
    ],

    "finance": [
        "accounting",
        "financial_planning_analysis",
        "corporate_finance",
        "investment_finance",
    ],

    "hr_recruiting": [
        "recruiting",
        "talent_acquisition",
        "people_operations",
        "human_resources",
    ],

    "customer_support": [
        "customer_support",
        "technical_support",
    ],

    "customer_success": [
        "customer_success_management",
        "implementation",
        "solutions_consulting",
    ],

    "operations": [
        "business_operations",
        "general_operations",
        "supply_chain",
        "strategy_operations",
    ],

    "other": [],
}


ALL_SUBFAMILIES = sorted(
    {
        subfamily
        for values in SUBFAMILIES_BY_FAMILY.values()
        for subfamily in values
    }
)


RELATED_ROLES = [
    # Engineering
    "software_engineer",
    "software_developer",
    "backend_engineer",
    "frontend_engineer",
    "full_stack_engineer",
    "mobile_engineer",
    "ios_engineer",
    "android_engineer",
    "platform_engineer",
    "infrastructure_engineer",
    "product_engineer",
    "sde",
    "devops_engineer",
    "site_reliability_engineer",
    "cloud_engineer",
    "systems_engineer",

    # Data / ML
    "data_engineer",
    "analytics_engineer",
    "data_scientist",
    "data_analyst",
    "business_intelligence_analyst",
    "machine_learning_engineer",
    "ml_engineer",
    "ai_engineer",
    "research_scientist",

    # QA / Security
    "qa_engineer",
    "quality_engineer",
    "automation_engineer",
    "sdet",
    "security_engineer",
    "application_security_engineer",
    "security_analyst",

    # Product / Program
    "product_manager",
    "technical_product_manager",
    "program_manager",
    "technical_program_manager",
    "project_manager",

    # Design
    "product_designer",
    "ux_designer",
    "ui_designer",
    "graphic_designer",

    # Sales / Customer
    "account_executive",
    "sales_development_representative",
    "business_development_representative",
    "sales_engineer",
    "solutions_engineer",
    "account_manager",
    "customer_success_manager",
    "customer_support_specialist",
    "technical_support_engineer",

    # Marketing
    "marketing_manager",
    "product_marketing_manager",
    "growth_marketer",
    "content_marketer",
    "demand_generation_manager",

    # Finance
    "financial_analyst",
    "accountant",
    "fp_and_a_analyst",

    # HR
    "recruiter",
    "technical_recruiter",
    "talent_acquisition_specialist",
    "hr_generalist",
    "people_operations_specialist",

    # Operations
    "operations_manager",
    "business_operations_analyst",
    "strategy_operations",
]


SENIORITY_LEVELS = [
    "intern",
    "entry",
    "mid",
    "senior",
    "staff",
    "principal",
    "lead",
    "manager",
    "director",
    "vp",
    "executive",
    "unknown",
]