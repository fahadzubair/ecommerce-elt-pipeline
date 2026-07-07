{#
    Use custom schemas exactly as written (e.g. "cleansed"), instead of dbt's
    default behavior of prefixing them with the target schema ("raw_cleansed").
    Falls back to the profile's target schema when a model has no +schema set.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}

    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}

{%- endmacro %}
