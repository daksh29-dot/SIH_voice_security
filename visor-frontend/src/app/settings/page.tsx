import { PageWrapper } from "@/components/layout/PageWrapper";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";

export default function SettingsPage() {
  return (
    <PageWrapper className="p-6 max-w-4xl mx-auto space-y-6">
      <h1 className="text-2xl font-light tracking-tight">System Configuration</h1>
      
      <Card>
        <CardHeader>
          <CardTitle>Acoustic Model Thresholds</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex justify-between items-center py-2 border-b border-border">
            <div>
              <p className="font-medium text-sm">Strict Anti-Spoofing (W2V2-AASIST)</p>
              <p className="text-xs text-text-secondary">Current threshold: 0.60</p>
            </div>
            <Button variant="outline" size="sm">Configure</Button>
          </div>
          <div className="flex justify-between items-center py-2">
            <div>
              <p className="font-medium text-sm">Automated Banking Freeze</p>
              <p className="text-xs text-text-secondary">Triggered on &gt; 0.6 Composite Risk</p>
            </div>
            <Button variant="outline" size="sm">Configure</Button>
          </div>
        </CardContent>
      </Card>
    </PageWrapper>
  );
}

