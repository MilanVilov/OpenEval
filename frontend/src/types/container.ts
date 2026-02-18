export interface Container {
  id: string;
  openai_container_id: string;
  name: string;
  file_count: number;
  status: string;
  created_at: string;
}

export interface CreateContainerRequest {
  name: string;
}
