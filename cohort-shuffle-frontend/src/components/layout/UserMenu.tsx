"use client";

import { signOut } from "next-auth/react";
import { useSession } from "next-auth/react";
import { LogOut, User } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";

function getInitials(name: string): string {
  return name
    .split(" ")
    .map((n) => n[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

export function UserMenu() {
  const { data: session } = useSession();
  const user = session?.user;

  if (!user) return null;

  const handleSignOut = () => {
    localStorage.removeItem("cohort_shuffle:activeCohortId");
    signOut({ callbackUrl: "/sign-in" });
  };

  return (
    <DropdownMenu>
      {/* DropdownMenuTrigger from @base-ui/react renders its own element.
          We style it as a ghost button and place the Avatar inside. */}
      <DropdownMenuTrigger
        aria-label="User menu"
        className="flex items-center rounded-full outline-none ring-offset-background focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
      >
        <Avatar className="h-8 w-8">
          <AvatarImage src={user.image ?? ""} alt={user.name ?? "User"} />
          <AvatarFallback>
            {user.name ? getInitials(user.name) : <User className="h-4 w-4" />}
          </AvatarFallback>
        </Avatar>
      </DropdownMenuTrigger>

      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel className="font-normal">
          <div className="flex flex-col gap-1">
            <p className="text-sm font-medium leading-none">{user.name}</p>
            <p className="text-xs leading-none text-muted-foreground">
              {user.email}
            </p>
            <Badge
              variant={user.role === "admin" ? "default" : "secondary"}
              className="mt-1 w-fit text-xs"
            >
              {user.role === "admin" ? "Admin" : "Student"}
            </Badge>
          </div>
        </DropdownMenuLabel>

        <DropdownMenuSeparator />

        <DropdownMenuItem
          onClick={handleSignOut}
          className="cursor-pointer text-destructive focus:text-destructive"
        >
          <LogOut className="mr-2 h-4 w-4" />
          Sign out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
