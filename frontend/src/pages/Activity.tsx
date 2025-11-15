import { useState, useEffect } from "react";
import { Search, Instagram, MessageCircle, Globe, MoreVertical, Send, Paperclip, Loader2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { EmptyState } from "@/components/shared/EmptyState";
import { MessageBubble } from "@/components/shared/MessageBubble";
import { cn } from "@/lib/utils";
import { 
  getConversations, 
  getConversationDetail, 
  replyToConversation, 
  updateConversationStatus,
  formatRelativeTime,
  getChannelDisplayName,
  getStatusColor,
  type Conversation,
  type ConversationDetail as ConversationDetailType,
  type ConversationMessage
} from "@/lib/api-conversations";
import { useToast } from "@/hooks/use-toast";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";


export default function Activity() {
  const { toast } = useToast();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedConversation, setSelectedConversation] = useState<string | null>(null);
  const [conversationDetail, setConversationDetail] = useState<ConversationDetailType | null>(null);
  const [channel, setChannel] = useState<string>("all");
  const [status, setStatus] = useState<string>("all");
  const [replyText, setReplyText] = useState("");
  const [loading, setLoading] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [sendingReply, setSendingReply] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  const loadConversations = async () => {
    try {
      setLoading(true);
      const data = await getConversations(channel, status);
      setConversations(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error("Error loading conversations:", error);
      setConversations([]);
      toast({
        title: "Erreur",
        description: "Impossible de charger les conversations",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  // Charger les détails d'une conversation
  const loadConversationDetail = async (conversationId: string) => {
    try {
      setLoadingDetail(true);
      const detail = await getConversationDetail(conversationId);
      setConversationDetail(detail);
    } catch (error) {
      toast({
        title: "Erreur",
        description: "Impossible de charger la conversation",
        variant: "destructive",
      });
    } finally {
      setLoadingDetail(false);
    }
  };

  // Envoyer une réponse
  const handleSendReply = async () => {
    if (!selectedConversation || !replyText.trim() || sendingReply) return;

    try {
      setSendingReply(true);
      await replyToConversation(selectedConversation, replyText);
      setReplyText("");
      
      // Recharger les détails de la conversation
      await loadConversationDetail(selectedConversation);
      
      toast({
        title: "Succès",
        description: "Réponse envoyée",
      });
    } catch (error) {
      toast({
        title: "Erreur",
        description: "Impossible d'envoyer la réponse",
        variant: "destructive",
      });
    } finally {
      setSendingReply(false);
    }
  };

  // Mettre à jour le statut d'une conversation
  const handleStatusUpdate = async (conversationId: string, newStatus: "active" | "resolved" | "escalated") => {
    try {
      await updateConversationStatus(conversationId, newStatus);
      
      // Recharger les conversations
      await loadConversations();
      
      toast({
        title: "Succès",
        description: `Conversation marquée comme ${newStatus}`,
      });
    } catch (error) {
      toast({
        title: "Erreur",
        description: "Impossible de mettre à jour le statut",
        variant: "destructive",
      });
    }
  };

  // Sélectionner une conversation
  const handleSelectConversation = (conversationId: string) => {
    setSelectedConversation(conversationId);
    loadConversationDetail(conversationId);
  };

  // Filtrer les conversations
  const filteredConversations = conversations.filter(conv => {
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      return (
        conv.platform_username?.toLowerCase().includes(query) ||
        conv.last_message?.toLowerCase().includes(query) ||
        conv.platform.toLowerCase().includes(query)
      );
    }
    return true;
  });

  useEffect(() => {
    loadConversations();
  }, [channel, status]);

  const getChannelIcon = (channel: string) => {
    switch (channel.toLowerCase()) {
      case "instagram":
        return <Instagram className="h-3 w-3" />;
      case "whatsapp":
        return <MessageCircle className="h-3 w-3" />;
      case "website":
      case "web":
      case "playground":
        return <Globe className="h-3 w-3" />;
      default:
        return <Globe className="h-3 w-3" />;
    }
  };

  return (
    <div className="flex gap-6 h-[calc(100vh-8rem)]">
      {/* Filters */}
      <div className="w-64 shrink-0 space-y-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Filters</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm font-medium mb-2 block">Channel</label>
              <Tabs value={channel} onValueChange={setChannel}>
                <TabsList className="grid w-full grid-cols-2">
                  <TabsTrigger value="all" className="text-xs">All</TabsTrigger>
                  <TabsTrigger value="instagram" className="text-xs">
                    <Instagram className="h-3 w-3" />
                  </TabsTrigger>
                </TabsList>
              </Tabs>
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">Status</label>
              <Select value={status} onValueChange={setStatus}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All</SelectItem>
                  <SelectItem value="active">Active</SelectItem>
                  <SelectItem value="resolved">Resolved</SelectItem>
                  <SelectItem value="escalated">Escalated</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input 
                placeholder="Search..." 
                className="pl-9" 
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Conversations List */}
      <div className="w-[360px] shrink-0">
        <Card className="h-full">
          <CardHeader>
            <CardTitle className="text-lg">Conversations</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {loading ? (
              <div className="flex items-center justify-center p-8">
                <Loader2 className="h-6 w-6 animate-spin" />
                <span className="ml-2">Chargement...</span>
              </div>
            ) : filteredConversations.length === 0 ? (
              <div className="p-8 text-center text-muted-foreground">
                {searchQuery ? "Aucune conversation trouvée" : "Aucune conversation"}
              </div>
            ) : (
              <div className="divide-y">
                {filteredConversations.map((conv) => (
                  <button
                    key={conv.id}
                    onClick={() => handleSelectConversation(conv.id)}
                    className={cn(
                      "w-full p-4 text-left hover:bg-accent transition-smooth",
                      selectedConversation === conv.id && "bg-accent border-l-2 border-primary"
                    )}
                  >
                    <div className="flex items-start gap-3">
                      <div className="relative">
                        <Avatar className="h-10 w-10">
                          <AvatarFallback>
                            {conv.platform_username?.split(" ").map((n) => n[0]).join("") || "U"}
                          </AvatarFallback>
                        </Avatar>
                        {conv.unread_count > 0 && (
                          <div className="absolute -top-1 -right-1 h-3 w-3 rounded-full bg-primary" />
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-2 mb-1">
                          <span className="font-medium text-sm truncate">
                            {conv.platform_username || `User ${conv.platform_user_id?.slice(0, 8) || 'Unknown'}`}
                          </span>
                          <span className="text-xs text-muted-foreground shrink-0">
                            {formatRelativeTime(conv.updated_at)}
                          </span>
                        </div>
                        <p className="text-sm text-muted-foreground truncate mb-2">
                          {conv.last_message || "Pas de message"}
                        </p>
                        <div className="flex items-center gap-2">
                          <Badge variant="secondary" className="h-5 px-2 text-xs">
                            {getChannelIcon(conv.platform)}
                            <span className="ml-1">{getChannelDisplayName(conv.platform)}</span>
                          </Badge>
                          {conv.status === "escalated" && (
                            <Badge variant="destructive" className="h-5 px-2 text-xs">
                              Escalated
                            </Badge>
                          )}
                          {conv.status === "resolved" && (
                            <Badge variant="outline" className="h-5 px-2 text-xs">
                              Resolved
                            </Badge>
                          )}
                        </div>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Chat View */}
      <Card className="flex-1 flex flex-col">
        {conversationDetail ? (
          <>
            <CardHeader className="border-b">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Avatar className="h-10 w-10">
                    <AvatarFallback>
                      {conversationDetail.conversation.platform_username?.split(" ").map((n) => n[0]).join("") || "U"}
                    </AvatarFallback>
                  </Avatar>
                  <div>
                    <h3 className="font-semibold">
                      {conversationDetail.conversation.platform_username || 
                       `User ${conversationDetail.conversation.platform_user_id?.slice(0, 8) || 'Unknown'}`}
                    </h3>
                    <div className="flex items-center gap-2">
                      <Badge variant="secondary" className="h-5 px-2 text-xs">
                        {getChannelIcon(conversationDetail.conversation.platform)}
                        <span className="ml-1">{getChannelDisplayName(conversationDetail.conversation.platform)}</span>
                      </Badge>
                      <Badge className={cn("h-5 px-2 text-xs", getStatusColor(conversationDetail.conversation.status))}>
                        {conversationDetail.conversation.status}
                      </Badge>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Button 
                    variant="outline" 
                    size="sm"
                    onClick={() => handleStatusUpdate(conversationDetail.conversation.id, "resolved")}
                    disabled={conversationDetail.conversation.status === "resolved"}
                  >
                    Resolve
                  </Button>
                  <Button 
                    variant="outline" 
                    size="sm"
                    onClick={() => handleStatusUpdate(conversationDetail.conversation.id, "escalated")}
                    disabled={conversationDetail.conversation.status === "escalated"}
                  >
                    Escalate
                  </Button>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="icon">
                        <MoreVertical className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem onClick={() => handleStatusUpdate(conversationDetail.conversation.id, "active")}>
                        Mark as Active
                      </DropdownMenuItem>
                      <DropdownMenuItem>View Profile</DropdownMenuItem>
                      <DropdownMenuItem className="text-destructive">Delete Conversation</DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
              </div>
            </CardHeader>
            <CardContent className="flex-1 flex flex-col p-0">
              <div className="flex-1 overflow-auto p-6">
                {loadingDetail ? (
                  <div className="flex items-center justify-center p-8">
                    <Loader2 className="h-6 w-6 animate-spin" />
                    <span className="ml-2">Chargement des messages...</span>
                  </div>
                ) : conversationDetail.messages.length === 0 ? (
                  <div className="p-8 text-center text-muted-foreground">
                    Aucun message dans cette conversation
                  </div>
                ) : (
                  <div className="space-y-4">
                    {conversationDetail.messages.map((message) => (
                      <MessageBubble
                        key={message.id}
                        role={message.role as "user" | "assistant" | "system"}
                        content={message.content}
                        timestamp={new Date(message.timestamp).toLocaleTimeString([], { 
                          hour: '2-digit', 
                          minute: '2-digit' 
                        })}
                      />
                    ))}
                  </div>
                )}
              </div>
              <div className="border-t p-4">
                <div className="flex gap-2">
                  <Textarea
                    placeholder="Type your reply... (Shift+Enter for new line)"
                    value={replyText}
                    onChange={(e) => setReplyText(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        handleSendReply();
                      }
                    }}
                    className="min-h-[80px] resize-none"
                    disabled={sendingReply}
                  />
                  <div className="flex flex-col gap-2">
                    <Button 
                      size="icon" 
                      onClick={handleSendReply}
                      disabled={sendingReply || !replyText.trim()}
                    >
                      {sendingReply ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Send className="h-4 w-4" />
                      )}
                    </Button>
                    <Button variant="outline" size="icon">
                      <Paperclip className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </div>
            </CardContent>
          </>
        ) : (
          <EmptyState
            icon={MessageCircle}
            title="No conversation selected"
            description="Select a conversation from the list to view and respond to messages."
          />
        )}
      </Card>
    </div>
  );
}
