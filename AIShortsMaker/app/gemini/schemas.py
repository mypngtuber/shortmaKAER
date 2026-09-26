from app.models.shorts import Analysis, Short

# SDK response_json_schema is derived from these Pydantic types.
RESPONSE_SCHEMA = Analysis.model_json_schema()
