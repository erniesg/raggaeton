def test_load_gcp_secrets():
    import os
    from dotenv import load_dotenv
    from raggaeton.backend.src.utils.common import ConfigLoader, base_dir

    # Load the environment variables from the .env file
    dotenv_path = os.path.join(base_dir, ".env")
    load_dotenv(dotenv_path)

    # Get the GCP credentials path and project ID from the environment variables
    gcp_credentials_path = os.getenv("GCP_CREDENTIALS_PATH")
    project_id = os.getenv("GCP_PROJECT_ID")

    # Create an instance of ConfigLoader
    config_loader = ConfigLoader()

    # Print debug information
    print("GCP Credentials Path:", gcp_credentials_path)
    print("Project ID:", project_id)
    print(
        "Loaded Secrets from GCP:",
        {k: v[-3:] for k, v in config_loader.secrets.items()},
    )

    # Assert that the secrets are loaded correctly
    assert config_loader.secrets["OPENAI_API_KEY"] is not None
    assert config_loader.secrets["CLAUDE_API_KEY"] is not None
    assert config_loader.secrets["GOOGLE_API_KEY"] is not None
    assert config_loader.secrets["GOOGLE_SEARCH_ENGINE_ID"] is not None
    assert config_loader.secrets["SUPABASE_PW"] is not None
    assert config_loader.secrets["SUPABASE_KEY"] is not None

    # Print environment variables for comparison
    print("Environment OPENAI_API_KEY:", os.environ.get("OPENAI_API_KEY")[-3:])
    print("Environment CLAUDE_API_KEY:", os.environ.get("CLAUDE_API_KEY")[-3:])
    print("Environment GOOGLE_API_KEY:", os.environ.get("GOOGLE_API_KEY")[-3:])
    print(
        "Environment GOOGLE_SEARCH_ENGINE_ID:",
        os.environ.get("GOOGLE_SEARCH_ENGINE_ID")[-3:],
    )
    print("Environment SUPABASE_PW:", os.environ.get("SUPABASE_PW")[-3:])
    print("Environment SUPABASE_KEY:", os.environ.get("SUPABASE_KEY")[-3:])

    # Assert that the environment variables are set correctly
    assert os.environ.get("OPENAI_API_KEY") == config_loader.secrets["OPENAI_API_KEY"]
    assert os.environ.get("CLAUDE_API_KEY") == config_loader.secrets["CLAUDE_API_KEY"]
    assert os.environ.get("GOOGLE_API_KEY") == config_loader.secrets["GOOGLE_API_KEY"]
    assert (
        os.environ.get("GOOGLE_SEARCH_ENGINE_ID")
        == config_loader.secrets["GOOGLE_SEARCH_ENGINE_ID"]
    )
    assert os.environ.get("SUPABASE_PW") == config_loader.secrets["SUPABASE_PW"]
    assert os.environ.get("SUPABASE_KEY") == config_loader.secrets["SUPABASE_KEY"]
