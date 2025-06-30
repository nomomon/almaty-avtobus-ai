import { BusFront } from "lucide-react";

const Logo = () => (
  <div className="flex items-center gap-2 text-lg font-semibold text-primary">
    <div className="flex items-center  justify-center h-8 w-8 bg-yellow-600/90 rounded-md">
      <BusFront className="h-6 w-6 text-primary-foreground" />
    </div>
    <span className="text-2xl font-bold">Almaty Avtobus AI</span>
  </div>
);

export default Logo;
