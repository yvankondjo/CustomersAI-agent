import { Instagram, MessageCircle, Facebook, Copy, Check, Calendar, Plus, Trash2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
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
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Switch } from "@/components/ui/switch";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useState, useEffect } from "react";
import { useToast } from "@/hooks/use-toast";
import {
  getSocialAccounts,
  connectPlatform,
  disconnectAccount,
  saveCalConfig,
  getCalConfig,
  removeCalConfig,
  type SocialAccount,
  type CalConfig,
} from "@/lib/api-social";

export default function Connect() {
  const { toast } = useToast();
  const [copied, setCopied] = useState(false);
  const [widgetColor, setWidgetColor] = useState("#0ea5e9");
  const [widgetTitle, setWidgetTitle] = useState("AI Support");
  const [widgetSubtitle, setWidgetSubtitle] = useState("We're here to help");
  const [widgetPosition, setWidgetPosition] = useState("bottom-right");
  const [showBranding, setShowBranding] = useState(true);

  // Social accounts state
  const [socialAccounts, setSocialAccounts] = useState<SocialAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [connectingInstagram, setConnectingInstagram] = useState(false);

  // Cal.com state
  const [calConfig, setCalConfig] = useState<CalConfig | null>(null);
  const [calDialogOpen, setCalDialogOpen] = useState(false);
  const [calApiKey, setCalApiKey] = useState("");
  const [calEventTypeId, setCalEventTypeId] = useState("");
  const [savingCalConfig, setSavingCalConfig] = useState(false);

  // Load social accounts
  useEffect(() => {
    loadSocialAccounts();
    loadCalConfig();
  }, []);

  const loadSocialAccounts = async () => {
    try {
      setLoading(true);
      const accounts = await getSocialAccounts();
      setSocialAccounts(accounts);
    } catch (error) {
      console.error("Error loading social accounts:", error);
      toast({
        title: "Error",
        description: "Failed to load social accounts",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const loadCalConfig = async () => {
    try {
      const config = await getCalConfig();
      setCalConfig(config);
      if (config) {
        setCalApiKey(config.api_key);
        setCalEventTypeId(config.event_type_id.toString());
      }
    } catch (error) {
      console.error("Error loading Cal config:", error);
    }
  };

  const handleConnectInstagram = async () => {
    if (connectingInstagram) return;
    try {
      setConnectingInstagram(true);
      await connectPlatform("instagram");
    } catch (error) {
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to connect Instagram",
        variant: "destructive",
      });
      setConnectingInstagram(false);
    }
  };

  const handleDisconnect = async (accountId: string, platform: string) => {
    const success = await disconnectAccount(accountId);
    if (success) {
      toast({
        title: "Disconnected",
        description: `${platform} account disconnected successfully`,
      });
      loadSocialAccounts();
    } else {
      toast({
        title: "Error",
        description: "Failed to disconnect account",
        variant: "destructive",
      });
    }
  };

  const handleSaveCalConfig = async () => {
    if (savingCalConfig) return;
    if (!calApiKey || !calEventTypeId) {
      toast({
        title: "Error",
        description: "Please enter both API key and Event Type ID",
        variant: "destructive",
      });
      return;
    }

    try {
      setSavingCalConfig(true);
      const config: CalConfig = {
        api_key: calApiKey,
        event_type_id: parseInt(calEventTypeId),
        timezone: "Europe/Paris",
      };

      const success = await saveCalConfig(config);
      if (success) {
        setCalConfig(config);
        setCalDialogOpen(false);
        toast({
          title: "Success",
          description: "Cal.com configuration saved",
        });
      } else {
        toast({
          title: "Error",
          description: "Failed to save configuration",
          variant: "destructive",
        });
      }
    } catch (error) {
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to save configuration",
        variant: "destructive",
      });
    } finally {
      setSavingCalConfig(false);
    }
  };

  const handleRemoveCalConfig = async () => {
    const success = await removeCalConfig();
    if (success) {
      setCalConfig(null);
      setCalApiKey("");
      setCalEventTypeId("");
      toast({
        title: "Removed",
        description: "Cal.com configuration removed",
      });
    }
  };

  const handleCopy = () => {
    const apiUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
    const widgetUrl = `${window.location.origin}/widget.js`;
    
    const embedCode = `<script src="${widgetUrl}"></script>
<script>
  AISupportWidget.init({
    baseUrl: '${apiUrl}',
    primaryColor: '${widgetColor}',
    title: '${widgetTitle}',
    subtitle: '${widgetSubtitle}',
    position: '${widgetPosition}',
    showBranding: ${showBranding}
  });
</script>`;

    navigator.clipboard.writeText(embedCode);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
    toast({
      title: "Copié !",
      description: "Code d'intégration copié dans le presse-papiers",
    });
  };

  // Get Instagram account if exists
  const instagramAccount = socialAccounts.find((acc) => acc.platform === "instagram");

  return (
    <div className="space-y-6">
      {/* Social Media Cards */}
      <div className="grid gap-6 md:grid-cols-3">
        {/* Instagram */}
        <Card className="relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-purple-500 via-pink-500 to-orange-500 opacity-10" />
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Instagram className="h-5 w-5" />
                <CardTitle className="text-lg">Instagram</CardTitle>
              </div>
              {instagramAccount && (
                <Badge variant="secondary" className="bg-green-500/10 text-green-600 border-green-500/20">
                  Connected
                </Badge>
              )}
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {loading ? (
              <div className="text-center text-sm text-muted-foreground">Loading...</div>
            ) : instagramAccount ? (
              <>
                <div className="flex items-center gap-3">
                  <Avatar className="h-12 w-12">
                    {instagramAccount.metadata?.profile_picture_url ? (
                      <AvatarImage src={instagramAccount.metadata.profile_picture_url} />
                    ) : (
                      <AvatarFallback>
                        {instagramAccount.account_username?.slice(0, 2).toUpperCase() || "IG"}
                      </AvatarFallback>
                    )}
                  </Avatar>
                  <div>
                    <p className="font-medium">@{instagramAccount.account_username}</p>
                    {instagramAccount.metadata?.follower_count && (
                      <p className="text-sm text-muted-foreground">
                        {instagramAccount.metadata.follower_count.toLocaleString()} followers
                      </p>
                    )}
                  </div>
                </div>
                {instagramAccount.metadata?.biography && (
                  <p className="text-xs text-muted-foreground line-clamp-2">
                    {instagramAccount.metadata.biography}
                  </p>
                )}
                <Button
                  variant="outline"
                  className="w-full"
                  onClick={() => handleDisconnect(instagramAccount.id, "Instagram")}
                >
                  <Trash2 className="h-4 w-4 mr-2" />
                  Disconnect
                </Button>
              </>
            ) : (
              <>
                <p className="text-sm text-muted-foreground">
                  Connect your Instagram account to handle customer conversations via DMs.
                </p>
                <Button 
                  className="w-full" 
                  onClick={handleConnectInstagram}
                  disabled={connectingInstagram}
                >
                  <Instagram className="h-4 w-4 mr-2" />
                  {connectingInstagram ? "Connecting..." : "Connect Instagram"}
                </Button>
              </>
            )}
          </CardContent>
        </Card>

        {/* Cal.com */}
        <Card className="relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-blue-500 to-cyan-500 opacity-10" />
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Calendar className="h-5 w-5" />
                <CardTitle className="text-lg">Cal.com</CardTitle>
              </div>
              {calConfig && (
                <Badge variant="secondary" className="bg-green-500/10 text-green-600 border-green-500/20">
                  Connected
                </Badge>
              )}
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {calConfig ? (
              <>
                <div className="space-y-2">
                  <div className="text-sm">
                    <span className="text-muted-foreground">Event Type ID:</span>
                    <span className="ml-2 font-mono">{calConfig.event_type_id}</span>
                  </div>
                  <div className="text-sm">
                    <span className="text-muted-foreground">Timezone:</span>
                    <span className="ml-2">{calConfig.timezone}</span>
                  </div>
                </div>
                <div className="flex gap-2">
                  <Dialog open={calDialogOpen} onOpenChange={setCalDialogOpen}>
                    <DialogTrigger asChild>
                      <Button variant="outline" className="flex-1">
                        Edit Config
                      </Button>
                    </DialogTrigger>
                    <DialogContent>
                      <DialogHeader>
                        <DialogTitle>Cal.com Configuration</DialogTitle>
                        <DialogDescription>
                          Update your Cal.com API credentials for appointment booking.
                        </DialogDescription>
                      </DialogHeader>
                      <div className="space-y-4 py-4">
                        <div className="space-y-2">
                          <Label htmlFor="cal-api-key">API Key</Label>
                          <Input
                            id="cal-api-key"
                            value={calApiKey}
                            onChange={(e) => setCalApiKey(e.target.value)}
                            placeholder="cal_live_xxxxx"
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="cal-event-type-id">Event Type ID</Label>
                          <Input
                            id="cal-event-type-id"
                            type="number"
                            value={calEventTypeId}
                            onChange={(e) => setCalEventTypeId(e.target.value)}
                            placeholder="123456"
                          />
                        </div>
                      </div>
                      <DialogFooter>
                        <Button onClick={handleSaveCalConfig} disabled={savingCalConfig}>
                          {savingCalConfig ? "Saving..." : "Save Configuration"}
                        </Button>
                      </DialogFooter>
                    </DialogContent>
                  </Dialog>
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={handleRemoveCalConfig}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </>
            ) : (
              <>
                <p className="text-sm text-muted-foreground">
                  Connect Cal.com to enable appointment booking in conversations.
                </p>
                <Dialog open={calDialogOpen} onOpenChange={setCalDialogOpen}>
                  <DialogTrigger asChild>
                    <Button className="w-full">
                      <Plus className="h-4 w-4 mr-2" />
                      Configure Cal.com
                    </Button>
                  </DialogTrigger>
                  <DialogContent>
                    <DialogHeader>
                      <DialogTitle>Cal.com Configuration</DialogTitle>
                      <DialogDescription>
                        Enter your Cal.com API credentials to enable appointment booking.
                      </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4 py-4">
                      <div className="space-y-2">
                        <Label htmlFor="cal-api-key">API Key</Label>
                        <Input
                          id="cal-api-key"
                          value={calApiKey}
                          onChange={(e) => setCalApiKey(e.target.value)}
                          placeholder="cal_live_xxxxx"
                        />
                        <p className="text-xs text-muted-foreground">
                          Get your API key from Cal.com Settings → Developer
                        </p>
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="cal-event-type-id">Event Type ID</Label>
                        <Input
                          id="cal-event-type-id"
                          type="number"
                          value={calEventTypeId}
                          onChange={(e) => setCalEventTypeId(e.target.value)}
                          placeholder="123456"
                        />
                        <p className="text-xs text-muted-foreground">
                          Create an Event Type in Cal.com and copy its ID
                        </p>
                      </div>
                    </div>
                    <DialogFooter>
                      <Button onClick={handleSaveCalConfig}>Save Configuration</Button>
                    </DialogFooter>
                  </DialogContent>
                </Dialog>
              </>
            )}
          </CardContent>
        </Card>

        {/* WhatsApp - Coming Soon */}
        <Card className="relative">
          <div className="absolute inset-0 bg-muted/50 backdrop-blur-sm flex items-center justify-center z-10">
            <Badge className="text-sm">Coming Soon</Badge>
          </div>
          <CardHeader>
            <div className="flex items-center gap-2">
              <MessageCircle className="h-5 w-5" />
              <CardTitle className="text-lg">WhatsApp</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-4">
              Connect your WhatsApp Business account to handle customer conversations.
            </p>
            <Button disabled className="w-full">Connect WhatsApp</Button>
          </CardContent>
        </Card>
      </div>

      {/* Web Widget */}
      <Card>
        <CardHeader>
          <CardTitle>Web Widget</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-6 lg:grid-cols-2">
            {/* Preview */}
            <div>
              <Label className="mb-3 block">Preview</Label>
              <div className="relative h-[480px] rounded-lg border bg-muted/30 overflow-hidden">
                <div className="absolute inset-0 flex items-center justify-center text-muted-foreground">
                  <div className="text-center">
                    <p className="text-sm mb-2">Your Website</p>
                    <p className="text-xs">Widget preview</p>
                  </div>
                </div>
                {/* Chat Widget */}
                <div className="absolute bottom-4 right-4 w-[340px] rounded-2xl shadow-2xl overflow-hidden border bg-background">
                  <div
                    className="p-4 text-white flex items-center gap-3"
                    style={{ backgroundColor: widgetColor }}
                  >
                    <Avatar className="h-10 w-10">
                      <AvatarFallback className="bg-white/20 text-white">AI</AvatarFallback>
                    </Avatar>
                    <div>
                      <p className="font-semibold">AI Support</p>
                      <p className="text-xs opacity-90">We're here to help</p>
                    </div>
                  </div>
                  <div className="p-4 bg-background space-y-3 h-[240px] overflow-auto">
                    <div className="flex gap-2">
                      <Avatar className="h-8 w-8 shrink-0">
                        <AvatarFallback className="text-xs bg-muted">AI</AvatarFallback>
                      </Avatar>
                      <div className="bg-muted rounded-lg px-3 py-2 text-sm max-w-[80%]">
                        Hi! How can I help you today?
                      </div>
                    </div>
                    <div className="flex gap-2 justify-end">
                      <div
                        className="rounded-lg px-3 py-2 text-sm text-white max-w-[80%]"
                        style={{ backgroundColor: widgetColor }}
                      >
                        I have a question about my order
                      </div>
                      <Avatar className="h-8 w-8 shrink-0">
                        <AvatarFallback className="text-xs bg-muted">U</AvatarFallback>
                      </Avatar>
                    </div>
                  </div>
                  <div className="p-4 border-t bg-background">
                    <Input placeholder="Type your message..." className="text-sm" />
                  </div>
                </div>
              </div>
            </div>

            {/* Customization */}
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="widgetTitle">Titre du Widget</Label>
                <Input 
                  id="widgetTitle" 
                  value={widgetTitle}
                  onChange={(e) => setWidgetTitle(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="widgetSubtitle">Sous-titre</Label>
                <Input 
                  id="widgetSubtitle" 
                  value={widgetSubtitle}
                  onChange={(e) => setWidgetSubtitle(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="widgetColor">Couleur principale</Label>
                <div className="flex gap-2">
                  <Input
                    id="widgetColor"
                    type="color"
                    value={widgetColor}
                    onChange={(e) => setWidgetColor(e.target.value)}
                    className="w-20 h-10 cursor-pointer"
                  />
                  <Input
                    value={widgetColor}
                    onChange={(e) => setWidgetColor(e.target.value)}
                    className="flex-1"
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="position">Position</Label>
                <Select value={widgetPosition} onValueChange={setWidgetPosition}>
                  <SelectTrigger id="position">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="bottom-right">En bas à droite</SelectItem>
                    <SelectItem value="bottom-left">En bas à gauche</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex items-center justify-between">
                <Label htmlFor="branding">Afficher le branding "Powered by"</Label>
                <Switch 
                  id="branding" 
                  checked={showBranding}
                  onCheckedChange={setShowBranding}
                />
              </div>

              <div className="pt-4">
                <Label className="mb-2 block">Code d'intégration</Label>
                <div className="relative">
                  <pre className="bg-muted p-4 rounded-lg text-xs overflow-x-auto max-h-48">
                    <code>{`<script src="${window.location.origin}/widget.js"></script>
<script>
  AISupportWidget.init({
    baseUrl: '${import.meta.env.VITE_API_URL || "http://localhost:8000"}',
    primaryColor: '${widgetColor}',
    title: '${widgetTitle}',
    subtitle: '${widgetSubtitle}',
    position: '${widgetPosition}',
    showBranding: ${showBranding}
  });
</script>`}</code>
                  </pre>
                  <Button
                    size="sm"
                    variant="secondary"
                    className="absolute top-2 right-2"
                    onClick={handleCopy}
                  >
                    {copied ? (
                      <Check className="h-4 w-4" />
                    ) : (
                      <Copy className="h-4 w-4" />
                    )}
                  </Button>
                </div>
              </div>

              <Alert>
                <AlertDescription className="text-sm">
                  Ajoutez ce code avant la balise fermante <code className="text-xs bg-muted px-1 py-0.5 rounded">&lt;/body&gt;</code> dans votre HTML.
                </AlertDescription>
              </Alert>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
