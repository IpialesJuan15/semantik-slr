import httpx
from backend.app.analysis import MODEL, MODEL_REPOSITORY, MODEL_REVISION, MODEL_PATH, CACHE, verify_model

if __name__ == '__main__':
    from fastembed import TextEmbedding
    from huggingface_hub import snapshot_download
    try:
        response = httpx.get('https://huggingface.co/api/models/Qdrant/paraphrase-multilingual-MiniLM-L12-v2-onnx-Q', timeout=15)
        response.raise_for_status()
    except httpx.HTTPError:
        raise SystemExit('No se pudo acceder a Hugging Face. Habilita huggingface.co y sus servidores de descarga en la red y vuelve a ejecutar este comando.')
    try:
        snapshot_download(repo_id=MODEL_REPOSITORY, revision=MODEL_REVISION, cache_dir=str(CACHE),
                          allow_patterns=['config.json','model_optimized.onnx','tokenizer.json','tokenizer_config.json','special_tokens_map.json'])
        verify_model()
        model = TextEmbedding(model_name=MODEL, cache_dir=str(CACHE), threads=2, specific_model_path=str(MODEL_PATH), local_files_only=True)
        vector = next(model.embed(['Inteligencia artificial en educación superior']))
    except Exception:
        raise SystemExit('La descarga o carga del modelo falló. Comprueba el espacio disponible y el acceso HTTPS a Hugging Face y us.aws.cdn.hf.co. Vuelve a ejecutar el comando; la caché conserva las descargas completadas.')
    print(f'Modelo listo: vector de {len(vector)} dimensiones. Ya puedes elegir análisis semántico.')
