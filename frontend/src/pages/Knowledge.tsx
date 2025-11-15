import { useState, useRef, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Globe, Upload, FileText, Plus, MoreVertical, ChevronDown, Loader2, CheckCircle2, XCircle, AlertCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/hooks/use-toast";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { ingestWebsite, ingestDocument, getJobStatus, listDocuments, listWebsites, deleteDocument, deleteWebsite, type JobStatus, type Document, type Website } from "@/lib/api";
import { createFAQ, listFAQs, updateFAQ, deleteFAQ, type FAQ } from "@/lib/api-faq";

export default function Knowledge() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [isAddFaqOpen, setIsAddFaqOpen] = useState(false);
  const [websiteUrl, setWebsiteUrl] = useState("");
  const [maxPages, setMaxPages] = useState(50);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [faqQuestion, setFaqQuestion] = useState("");
  const [faqVariants, setFaqVariants] = useState("");
  const [faqAnswer, setFaqAnswer] = useState("");
  const [faqCategory, setFaqCategory] = useState("general");
  const [editingFaq, setEditingFaq] = useState<FAQ | null>(null);

  const websiteMutation = useMutation({
    mutationFn: ingestWebsite,
    onSuccess: (data) => {
      setActiveJobId(data.job_id);
      toast({
        title: "Crawl démarré",
        description: "Le crawl du site web a été mis en file d'attente.",
      });
      refetchWebsites();
    },
    onError: (error: Error) => {
      toast({
        title: "Erreur",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  const documentMutation = useMutation({
    mutationFn: ingestDocument,
    onSuccess: (data) => {
      setActiveJobId(data.job_id);
      toast({
        title: "Traitement démarré",
        description: "Le traitement du document a été mis en file d'attente.",
      });
    },
    onError: (error: Error) => {
      toast({
        title: "Erreur",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  const { data: jobStatus } = useQuery<JobStatus>({
    queryKey: ["jobStatus", activeJobId],
    queryFn: () => getJobStatus(activeJobId!),
    enabled: !!activeJobId,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data?.status === "finished" || data?.status === "failed") {
        return false;
      }
      return 2000;
    },
  });

  const { data: faqs = [], refetch: refetchFAQs } = useQuery<FAQ[]>({
    queryKey: ["faqs"],
    queryFn: listFAQs,
  });

  const { data: documents = [], refetch: refetchDocuments } = useQuery<Document[]>({
    queryKey: ["documents"],
    queryFn: listDocuments,
    refetchInterval: 5000, // Refetch every 5 seconds to update status
  });

  const { data: websites = [], refetch: refetchWebsites } = useQuery<Website[]>({
    queryKey: ["websites"],
    queryFn: listWebsites,
    refetchInterval: 5000, // Refetch every 5 seconds to update status
  });

  const deleteDocumentMutation = useMutation({
    mutationFn: deleteDocument,
    onSuccess: () => {
      toast({
        title: "Document supprimé",
        description: "Le document a été supprimé avec succès.",
      });
      refetchDocuments();
    },
    onError: (error: Error) => {
      toast({
        title: "Erreur",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  const deleteWebsiteMutation = useMutation({
    mutationFn: deleteWebsite,
    onSuccess: () => {
      toast({
        title: "Page supprimée",
        description: "La page web a été supprimée avec succès.",
      });
      refetchWebsites();
    },
    onError: (error: Error) => {
      toast({
        title: "Erreur",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  const createFaqMutation = useMutation({
    mutationFn: createFAQ,
    onSuccess: () => {
      toast({
        title: "FAQ créée",
        description: "La FAQ a été créée avec succès.",
      });
      setIsAddFaqOpen(false);
      setFaqQuestion("");
      setFaqVariants("");
      setFaqAnswer("");
      setFaqCategory("general");
      refetchFAQs();
    },
    onError: (error: Error) => {
      toast({
        title: "Erreur",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  const updateFaqMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) => updateFAQ(id, data),
    onSuccess: () => {
      toast({
        title: "FAQ mise à jour",
        description: "La FAQ a été mise à jour avec succès.",
      });
      setEditingFaq(null);
      refetchFAQs();
    },
    onError: (error: Error) => {
      toast({
        title: "Erreur",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  const deleteFaqMutation = useMutation({
    mutationFn: deleteFAQ,
    onSuccess: () => {
      toast({
        title: "FAQ supprimée",
        description: "La FAQ a été supprimée avec succès.",
      });
      refetchFAQs();
    },
    onError: (error: Error) => {
      toast({
        title: "Erreur",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  const handleSaveFaq = () => {
    if (!faqQuestion.trim() || !faqAnswer.trim()) {
      toast({
        title: "Champs requis",
        description: "La question et la réponse sont obligatoires.",
        variant: "destructive",
      });
      return;
    }

    const variants = faqVariants
      .split("\n")
      .map((v) => v.trim())
      .filter((v) => v.length > 0);

    if (editingFaq) {
      updateFaqMutation.mutate({
        id: editingFaq.id,
        data: {
          question: faqQuestion,
          variants: variants,
          answer: faqAnswer,
          category: faqCategory,
        },
      });
    } else {
      createFaqMutation.mutate({
        question: faqQuestion,
        variants: variants,
        answer: faqAnswer,
        category: faqCategory,
      });
    }
  };

  const handleEditFaq = (faq: FAQ) => {
    setEditingFaq(faq);
    setFaqQuestion(faq.question);
    setFaqVariants(faq.variants.join("\n"));
    setFaqAnswer(faq.answer);
    setFaqCategory(faq.category || "general");
    setIsAddFaqOpen(true);
  };

  const handleDeleteFaq = (id: string) => {
    if (confirm("Êtes-vous sûr de vouloir supprimer cette FAQ ?")) {
      deleteFaqMutation.mutate(id);
    }
  };

  useEffect(() => {
    if (jobStatus?.status === "finished") {
      toast({
        title: "Terminé",
        description: "Le traitement est terminé avec succès.",
      });
      setActiveJobId(null);
      refetchWebsites();
      refetchDocuments();
    } else if (jobStatus?.status === "failed") {
      toast({
        title: "Échec",
        description: jobStatus.error || "Le traitement a échoué.",
        variant: "destructive",
      });
      setActiveJobId(null);
    }
  }, [jobStatus, toast, refetchWebsites, refetchDocuments]);

  const handleStartCrawl = () => {
    if (!websiteUrl.trim()) {
      toast({
        title: "URL requise",
        description: "Veuillez entrer une URL valide.",
        variant: "destructive",
      });
      return;
    }

    websiteMutation.mutate({
      url: websiteUrl,
      max_pages: maxPages,
    });
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    try {
      const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
      const uploadResponse = await fetch(`${API_BASE_URL}/api/v1/documents/upload`, {
        method: "POST",
        body: formData,
      });

      if (!uploadResponse.ok) {
        const error = await uploadResponse.json().catch(() => ({ detail: "Échec de l'upload" }));
        throw new Error(error.detail || "Échec de l'upload");
      }

      const uploadData = await uploadResponse.json();

      documentMutation.mutate({
        document_id: uploadData.document_id,
      });

      // Refetch documents to show the new one
      refetchDocuments();
    } catch (error) {
      toast({
        title: "Erreur",
        description: error instanceof Error ? error.message : "Échec de l'upload",
        variant: "destructive",
      });
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const files = e.dataTransfer.files;
    if (files.length > 0 && fileInputRef.current) {
      fileInputRef.current.files = files;
      handleFileUpload({ target: { files } } as any);
    }
  };

  const getStatusIcon = (status?: string) => {
    switch (status) {
      case "finished":
        return <CheckCircle2 className="h-4 w-4 text-green-500" />;
      case "failed":
        return <XCircle className="h-4 w-4 text-red-500" />;
      case "started":
        return <Loader2 className="h-4 w-4 animate-spin text-blue-500" />;
      default:
        return <AlertCircle className="h-4 w-4 text-yellow-500" />;
    }
  };

  const getStatusBadge = (status?: string) => {
    switch (status) {
      case "finished":
      case "processed":
        return <Badge className="bg-green-500">Terminé</Badge>;
      case "failed":
        return <Badge variant="destructive">Échoué</Badge>;
      case "started":
      case "processing":
        return <Badge className="bg-blue-500">En cours</Badge>;
      default:
        return <Badge variant="secondary">En attente</Badge>;
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <Tabs defaultValue="website" className="space-y-6">
      <TabsList>
        <TabsTrigger value="website">
          <Globe className="h-4 w-4 mr-2" />
          Website
        </TabsTrigger>
        <TabsTrigger value="data">
          <Upload className="h-4 w-4 mr-2" />
          Documents
        </TabsTrigger>
        <TabsTrigger value="faq">
          <FileText className="h-4 w-4 mr-2" />
          FAQ
        </TabsTrigger>
      </TabsList>

      <TabsContent value="website" className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Crawl Website</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="url">Website URL</Label>
              <div className="flex gap-2">
                <Input
                  id="url"
                  placeholder="https://example.com"
                  className="flex-1"
                  value={websiteUrl}
                  onChange={(e) => setWebsiteUrl(e.target.value)}
                  disabled={websiteMutation.isPending}
                />
                <Button 
                  onClick={handleStartCrawl} 
                  disabled={websiteMutation.isPending || !websiteUrl.trim()}
                >
                  {websiteMutation.isPending ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      En cours...
                    </>
                  ) : (
                    "Start Crawl"
                  )}
                </Button>
              </div>
            </div>

            <Collapsible>
              <CollapsibleTrigger asChild>
                <Button variant="ghost" size="sm" className="gap-2">
                  <ChevronDown className="h-4 w-4" />
                  Options avancées
                </Button>
              </CollapsibleTrigger>
              <CollapsibleContent className="space-y-4 pt-4">
                <div className="space-y-2">
                  <Label htmlFor="maxPages">Nombre de pages maximum</Label>
                  <Input 
                    id="maxPages" 
                    type="number" 
                    value={maxPages}
                    onChange={(e) => setMaxPages(parseInt(e.target.value) || 50)}
                    min="1" 
                    max="100" 
                  />
                  <p className="text-xs text-muted-foreground">
                    Nombre maximum de pages à crawler (1-100)
                  </p>
                </div>
              </CollapsibleContent>
            </Collapsible>

            {activeJobId && jobStatus && (
              <Card>
                <CardContent className="pt-6">
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        {getStatusIcon(jobStatus.status)}
                        <span className="font-medium">Statut du crawl</span>
                      </div>
                      {getStatusBadge(jobStatus.status)}
                    </div>
                    
                    {jobStatus.status === "started" && (
                      <Progress value={50} className="h-2" />
                    )}
                    
                    {jobStatus.result && (
                      <div className="grid grid-cols-3 gap-4 pt-4 text-center">
                        <div>
                          <div className="text-2xl font-bold">
                            {jobStatus.result.pages_crawled || 0}
                          </div>
                          <div className="text-xs text-muted-foreground">Pages crawlees</div>
                        </div>
                        <div>
                          <div className="text-2xl font-bold">
                            {jobStatus.result.total_chunks || 0}
                          </div>
                          <div className="text-xs text-muted-foreground">Chunks</div>
                        </div>
                        <div>
                          <div className="text-2xl font-bold">
                            {jobStatus.started_at ? 
                              Math.round((new Date().getTime() - new Date(jobStatus.started_at).getTime()) / 1000) 
                              : 0}s
                          </div>
                          <div className="text-xs text-muted-foreground">Durée</div>
                        </div>
                      </div>
                    )}
                    
                    {jobStatus.error && (
                      <div className="p-3 bg-red-50 border border-red-200 rounded-md">
                        <p className="text-sm text-red-800">{jobStatus.error}</p>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Pages indexées ({websites.length})</CardTitle>
          </CardHeader>
          <CardContent>
            {websites.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                Aucune page indexée pour le moment
              </div>
            ) : (
              <div className="space-y-3">
                {websites.map((website) => (
                  <Collapsible key={website.base_url}>
                    <div className="border rounded-lg">
                      <CollapsibleTrigger className="flex items-center justify-between w-full p-4 text-left hover:bg-accent transition-smooth">
                        <div className="flex items-center gap-3 flex-1">
                          <Globe className="h-5 w-5 text-muted-foreground" />
                          <div className="flex-1">
                            <p className="font-medium truncate">{website.base_url}</p>
                            <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
                              <span>{website.total_pages} page{website.total_pages !== 1 ? "s" : ""}</span>
                              <span>•</span>
                              <span>{website.total_chunks} chunk{website.total_chunks !== 1 ? "s" : ""}</span>
                            </div>
                          </div>
                          <ChevronDown className="h-4 w-4 text-muted-foreground" />
                        </div>
                      </CollapsibleTrigger>
                      <CollapsibleContent>
                        <div className="px-4 pb-4 space-y-2">
                          {website.pages.map((page) => (
                            <div key={page.id} className="flex items-center justify-between p-3 bg-accent/50 rounded-md">
                              <div className="flex-1 min-w-0">
                                <p className="text-sm font-medium truncate">{page.title || page.url}</p>
                                <p className="text-xs text-muted-foreground truncate">{page.url}</p>
                                <div className="flex items-center gap-2 mt-1">
                                  {page.chunk_count !== undefined && (
                                    <span className="text-xs text-muted-foreground">{page.chunk_count} chunks</span>
                                  )}
                                  {page.crawled_at && (
                                    <>
                                      <span className="text-xs text-muted-foreground">•</span>
                                      <span className="text-xs text-muted-foreground">{formatDate(page.crawled_at)}</span>
                                    </>
                                  )}
                                </div>
                              </div>
                              <DropdownMenu>
                                <DropdownMenuTrigger asChild>
                                  <Button variant="ghost" size="icon">
                                    <MoreVertical className="h-4 w-4" />
                                  </Button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent align="end">
                                  <DropdownMenuItem
                                    className="text-destructive"
                                    onClick={() => {
                                      if (confirm("Êtes-vous sûr de vouloir supprimer cette page ?")) {
                                        deleteWebsiteMutation.mutate(page.id);
                                      }
                                    }}
                                    disabled={deleteWebsiteMutation.isPending}
                                  >
                                    {deleteWebsiteMutation.isPending ? "Suppression..." : "Supprimer"}
                                  </DropdownMenuItem>
                                </DropdownMenuContent>
                              </DropdownMenu>
                            </div>
                          ))}
                        </div>
                      </CollapsibleContent>
                    </div>
                  </Collapsible>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </TabsContent>

      <TabsContent value="data" className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Upload Files</CardTitle>
          </CardHeader>
          <CardContent>
            <div
              className="border-2 border-dashed rounded-lg p-12 text-center hover:border-primary transition-colors cursor-pointer"
              onDragOver={handleDragOver}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <Upload className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
              <p className="text-lg font-medium mb-2">
                Glissez les fichiers ici ou cliquez pour parcourir
              </p>
              <p className="text-sm text-muted-foreground mb-4">
                Formats supportés : PDF, DOCX, TXT jusqu'à 10MB
              </p>
              <Button disabled={documentMutation.isPending}>
                {documentMutation.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Traitement...
                  </>
                ) : (
                  "Sélectionner des fichiers"
                )}
              </Button>
              <input
                ref={fileInputRef}
                type="file"
                className="hidden"
                accept=".pdf,.docx,.txt,.md"
                onChange={handleFileUpload}
              />
            </div>
          </CardContent>
        </Card>

        {activeJobId && jobStatus && documentMutation.isSuccess && (
          <Card>
            <CardContent className="pt-6">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {getStatusIcon(jobStatus.status)}
                    <span className="font-medium">Statut du traitement</span>
                  </div>
                  {getStatusBadge(jobStatus.status)}
                </div>
                
                {jobStatus.status === "started" && (
                  <Progress value={50} className="h-2" />
                )}
                
                {jobStatus.error && (
                  <div className="p-3 bg-red-50 border border-red-200 rounded-md">
                    <p className="text-sm text-red-800">{jobStatus.error}</p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        )}

        <Card>
          <CardHeader>
            <CardTitle>Fichiers uploadés ({documents.length})</CardTitle>
          </CardHeader>
          <CardContent>
            {documents.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                Aucun fichier uploadé pour le moment
              </div>
            ) : (
              <div className="space-y-2">
                {documents.map((doc) => (
                  <div key={doc.id} className="flex items-center justify-between p-4 border rounded-lg hover:bg-accent/50 transition-smooth">
                    <div className="flex items-center gap-3 flex-1 min-w-0">
                      <FileText className="h-5 w-5 text-muted-foreground flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="font-medium truncate">{doc.filename}</p>
                        <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
                          <span>{formatFileSize(doc.file_size)}</span>
                          <span>•</span>
                          <span>{formatDate(doc.created_at)}</span>
                          {doc.chunk_count !== undefined && doc.chunk_count > 0 && (
                            <>
                              <span>•</span>
                              <span>{doc.chunk_count} chunk{doc.chunk_count !== 1 ? "s" : ""}</span>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {getStatusBadge(doc.status)}
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon">
                            <MoreVertical className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem
                            className="text-destructive"
                            onClick={() => {
                              if (confirm("Êtes-vous sûr de vouloir supprimer ce document ?")) {
                                deleteDocumentMutation.mutate(doc.id);
                              }
                            }}
                            disabled={deleteDocumentMutation.isPending}
                          >
                            {deleteDocumentMutation.isPending ? "Suppression..." : "Supprimer"}
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </TabsContent>

      <TabsContent value="faq" className="space-y-6">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Questions fréquemment posées</CardTitle>
              <Dialog open={isAddFaqOpen} onOpenChange={(open) => {
                setIsAddFaqOpen(open);
                if (!open) {
                  setEditingFaq(null);
                  setFaqQuestion("");
                  setFaqVariants("");
                  setFaqAnswer("");
                  setFaqCategory("general");
                }
              }}>
                <DialogTrigger asChild>
                  <Button>
                    <Plus className="h-4 w-4 mr-2" />
                    Ajouter FAQ
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>{editingFaq ? "Modifier la FAQ" : "Ajouter une nouvelle FAQ"}</DialogTitle>
                    <DialogDescription>
                      Créez une nouvelle question fréquemment posée avec des variantes et une réponse.
                    </DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="question">Question</Label>
                      <Input 
                        id="question" 
                        placeholder="Quelle est votre politique de retour ?" 
                        value={faqQuestion}
                        onChange={(e) => setFaqQuestion(e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="variants">Variantes de question</Label>
                      <Textarea
                        id="variants"
                        placeholder="Une variante par ligne..."
                        className="min-h-[80px]"
                        value={faqVariants}
                        onChange={(e) => setFaqVariants(e.target.value)}
                      />
                      <p className="text-xs text-muted-foreground">
                        Ajoutez des façons alternatives dont les utilisateurs pourraient poser cette question
                      </p>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="answer">Réponse</Label>
                      <Textarea
                        id="answer"
                        placeholder="Notre politique de retour est..."
                        className="min-h-[150px]"
                        value={faqAnswer}
                        onChange={(e) => setFaqAnswer(e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="category">Catégorie</Label>
                      <Select value={faqCategory} onValueChange={setFaqCategory}>
                        <SelectTrigger id="category">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="shipping">Livraison</SelectItem>
                          <SelectItem value="returns">Retours</SelectItem>
                          <SelectItem value="products">Produits</SelectItem>
                          <SelectItem value="account">Compte</SelectItem>
                          <SelectItem value="general">Général</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="flex gap-2 justify-end">
                      <Button 
                        variant="outline" 
                        onClick={() => {
                          setIsAddFaqOpen(false);
                          setEditingFaq(null);
                        }}
                        disabled={createFaqMutation.isPending || updateFaqMutation.isPending}
                      >
                        Annuler
                      </Button>
                      <Button 
                        onClick={handleSaveFaq}
                        disabled={createFaqMutation.isPending || updateFaqMutation.isPending}
                      >
                        {createFaqMutation.isPending || updateFaqMutation.isPending ? (
                          <>
                            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                            Enregistrement...
                          </>
                        ) : (
                          editingFaq ? "Modifier FAQ" : "Enregistrer FAQ"
                        )}
                      </Button>
                    </div>
                  </div>
                </DialogContent>
              </Dialog>
            </div>
          </CardHeader>
          <CardContent>
            {faqs.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                Aucune FAQ pour le moment. Créez-en une pour commencer.
              </div>
            ) : (
              <div className="space-y-2">
                {faqs.map((faq) => (
                  <Collapsible key={faq.id}>
                    <div className="border rounded-lg">
                      <CollapsibleTrigger className="flex items-center justify-between w-full p-4 text-left hover:bg-accent transition-smooth">
                        <div className="flex items-center gap-3 flex-1">
                          <ChevronDown className="h-4 w-4 text-muted-foreground" />
                          <div>
                            <p className="font-medium">{faq.question}</p>
                            <div className="flex items-center gap-2 mt-1">
                              <Badge variant="secondary" className="text-xs">
                                {faq.category || "Général"}
                              </Badge>
                              <span className="text-xs text-muted-foreground">
                                {faq.variants?.length || 0} variante{faq.variants?.length !== 1 ? "s" : ""}
                              </span>
                            </div>
                          </div>
                        </div>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                            <Button variant="ghost" size="icon">
                              <MoreVertical className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem onClick={() => handleEditFaq(faq)}>
                              Modifier
                            </DropdownMenuItem>
                            <DropdownMenuItem 
                              className="text-destructive"
                              onClick={() => handleDeleteFaq(faq.id)}
                              disabled={deleteFaqMutation.isPending}
                            >
                              {deleteFaqMutation.isPending ? "Suppression..." : "Supprimer"}
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </CollapsibleTrigger>
                      <CollapsibleContent>
                        <div className="px-4 pb-4 space-y-3">
                          <div>
                            <p className="text-sm font-medium mb-2">Réponse :</p>
                            <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                              {faq.answer}
                            </p>
                          </div>
                          {faq.variants && faq.variants.length > 0 && (
                            <div>
                              <p className="text-sm font-medium mb-2">Variantes :</p>
                              <div className="flex flex-wrap gap-2">
                                {faq.variants.map((v, j) => (
                                  <Badge key={j} variant="outline">{v}</Badge>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      </CollapsibleContent>
                    </div>
                  </Collapsible>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </TabsContent>
    </Tabs>
  );
}
