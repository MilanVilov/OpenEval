export interface VectorStore {
  id: string;
  openai_vector_store_id: string;
  name: string;
  file_count: number;
  status: string;
  created_at: string;
}

export interface CreateVectorStoreRequest {
  name: string;
}
