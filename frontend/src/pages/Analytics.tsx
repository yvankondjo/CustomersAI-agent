import { useState } from "react";
import { TrendingUp, Clock, CheckCircle2, Zap, MessageSquare } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Progress } from "@/components/ui/progress";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

const chartData = [
  { date: "Mon", conversations: 45 },
  { date: "Tue", conversations: 52 },
  { date: "Wed", conversations: 48 },
  { date: "Thu", conversations: 61 },
  { date: "Fri", conversations: 55 },
  { date: "Sat", conversations: 38 },
  { date: "Sun", conversations: 42 },
];

const topTopics = [
  { rank: 1, topic: "Order status inquiry", count: 234, percentage: 28 },
  { rank: 2, topic: "Refund request", count: 189, percentage: 23 },
  { rank: 3, topic: "Product availability", count: 156, percentage: 19 },
  { rank: 4, topic: "Shipping delays", count: 142, percentage: 17 },
  { rank: 5, topic: "Account access", count: 98, percentage: 12 },
  { rank: 6, topic: "Payment issues", count: 87, percentage: 10 },
  { rank: 7, topic: "Product recommendations", count: 76, percentage: 9 },
  { rank: 8, topic: "Return policy", count: 65, percentage: 8 },
  { rank: 9, topic: "Technical support", count: 54, percentage: 6 },
  { rank: 10, topic: "Store locations", count: 43, percentage: 5 },
];

interface MetricCardProps {
  title: string;
  value: string;
  change: string;
  isPositive: boolean;
  icon: React.ComponentType<{ className?: string }>;
}

function MetricCard({ title, value, change, isPositive, icon: Icon }: MetricCardProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold mb-1">{value}</div>
        <p className={`text-xs ${isPositive ? "text-green-600" : "text-red-600"}`}>
          {isPositive ? "↑" : "↓"} {change} from last period
        </p>
      </CardContent>
    </Card>
  );
}

export default function Analytics() {
  const [timeRange, setTimeRange] = useState("7d");

  return (
    <div className="space-y-6">
      {/* Metrics Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          title="Total Conversations"
          value="1,234"
          change="12.5%"
          isPositive={true}
          icon={MessageSquare}
        />
        <MetricCard
          title="Avg Response Time"
          value="2m 34s"
          change="8.2%"
          isPositive={true}
          icon={Clock}
        />
        <MetricCard
          title="Resolution Rate"
          value="94.2%"
          change="3.1%"
          isPositive={true}
          icon={CheckCircle2}
        />
        <MetricCard
          title="AI Automation"
          value="78%"
          change="15.3%"
          isPositive={true}
          icon={Zap}
        />
      </div>

      {/* Trend Chart */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Conversation Volume</CardTitle>
            <Select value={timeRange} onValueChange={setTimeRange}>
              <SelectTrigger className="w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="7d">Last 7 days</SelectItem>
                <SelectItem value="30d">Last 30 days</SelectItem>
                <SelectItem value="90d">Last 90 days</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="colorConversations" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis
                dataKey="date"
                className="text-xs"
                stroke="hsl(var(--muted-foreground))"
              />
              <YAxis className="text-xs" stroke="hsl(var(--muted-foreground))" />
              <Tooltip
                contentStyle={{
                  backgroundColor: "hsl(var(--card))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: "var(--radius)",
                }}
              />
              <Area
                type="monotone"
                dataKey="conversations"
                stroke="hsl(var(--primary))"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#colorConversations)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Top Topics */}
      <Card>
        <CardHeader>
          <CardTitle>Top 10 Topics</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {topTopics.map((topic) => (
              <div key={topic.rank} className="flex items-center gap-4">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-muted text-sm font-semibold">
                  {topic.rank}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-1">
                    <p className="text-sm font-medium truncate">{topic.topic}</p>
                    <span className="text-sm text-muted-foreground ml-2">{topic.count}</span>
                  </div>
                  <Progress value={topic.percentage} className="h-2" />
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
