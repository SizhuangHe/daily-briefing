import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  addSource,
  deleteSource,
  fetchSources,
  toggleSource,
} from "../api/preferences";

export function useSources() {
  return useQuery({
    queryKey: ["sources"],
    queryFn: fetchSources,
  });
}

export function useAddSource() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: addSource,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["sources"] }),
  });
}

export function useToggleSource() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: toggleSource,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["sources"] }),
  });
}

export function useDeleteSource() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteSource,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["sources"] }),
  });
}
