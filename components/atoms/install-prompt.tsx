"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Download, Share, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter } from "@/components/ui/card";

// App info from manifest
const APP_NAME = "Almaty Bus AI";
const APP_DESCRIPTION = "An AI-powered assistant for Almaty public transport";
const APP_ICON = "/web-app-manifest-192x192.png";
const THEME_COLOR = "#d69300";

export default function InstallPrompt() {
  const [isIOS, setIsIOS] = useState(false);
  const [isStandalone, setIsStandalone] = useState(false);
  const [isVisible, setIsVisible] = useState(false);
  const [isDismissed, setIsDismissed] = useState(false);

  useEffect(() => {
    const iosCheck =
      /iPad|iPhone|iPod/.test(navigator.userAgent) && !(window as any).MSStream;
    const standaloneCheck = window.matchMedia(
      "(display-mode: standalone)",
    ).matches;

    setIsIOS(iosCheck);
    setIsStandalone(standaloneCheck);

    // Show the prompt after a short delay if not standalone and not dismissed
    if (!standaloneCheck && !isDismissed) {
      const timer = setTimeout(() => setIsVisible(true), 2000);
      return () => clearTimeout(timer);
    }
  }, [isDismissed]);

  const handleDismiss = () => {
    setIsVisible(false);
    setIsDismissed(true);
  };

  const handleInstall = () => {
    // For non-iOS devices, you could trigger the beforeinstallprompt event here
    // For now, we'll just show instructions
    setIsVisible(false);
  };

  if (isStandalone || isDismissed) {
    return null;
  }

  return (
    <AnimatePresence>
      {isVisible && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/20 backdrop-blur-sm z-40"
            onClick={handleDismiss}
          />

          {/* Install Prompt Card */}
          <motion.div
            initial={{ y: 100, opacity: 0, scale: 0.95 }}
            animate={{ y: 0, opacity: 1, scale: 1 }}
            exit={{ y: 100, opacity: 0, scale: 0.95 }}
            transition={{
              type: "spring",
              damping: 25,
              stiffness: 300,
              duration: 0.3,
            }}
            className="fixed bottom-4 left-4 right-4 z-50 max-w-sm mx-auto"
          >
            <Card className="relative border-0 shadow-2xl bg-white/95 backdrop-blur-md gap-2">
              {/* Close Button */}
              <Button
                variant="ghost"
                size="sm"
                onClick={handleDismiss}
                className="absolute top-4 right-4 h-8 w-8 p-0 text-gray-400 hover:text-gray-600. cursor-pointer"
              >
                <X className="w-4 h-4" />
              </Button>
              <CardContent className="p-6">
                <div className="flex items-start gap-4">
                  {/* App Icon */}
                  <div className="flex-shrink-0">
                    <div
                      className="w-12 h-12 rounded-xl flex items-center justify-center shadow-lg"
                      style={{ background: THEME_COLOR }}
                    >
                      <img
                        src={APP_ICON}
                        alt="App Icon"
                        className="w-10 h-10 rounded-lg"
                      />
                    </div>
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between">
                      <div>
                        <h3 className="font-semibold text-gray-900 text-lg">
                          Install {APP_NAME}
                        </h3>
                        <p className="text-sm text-gray-600 mt-.25">
                          {APP_DESCRIPTION}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
              <CardFooter>
                {/* iOS Instructions */}
                {isIOS ? (
                  <div className="space-y-3">
                    <p className="text-sm text-gray-700">
                      To install this app on your device:
                    </p>
                    <div className="flex items-center gap-2 text-sm text-gray-600">
                      <span>1. Tap the share button</span>
                      <Share className="w-4 h-4" />
                    </div>
                    <div className="flex items-center gap-2 text-sm text-gray-600">
                      <span>2. Select "Add to Home Screen"</span>
                      <Plus className="w-4 h-4" />
                    </div>
                  </div>
                ) : (
                  <Button
                    onClick={handleInstall}
                    className="w-full bg-gradient-to-r from-yellow-500 to-yellow-600 hover:from-yellow-600 hover:to-yellow-700 text-white font-medium cursor-pointer"
                    style={{ background: THEME_COLOR }}
                  >
                    <Download className="w-4 h-4 mr-2" />
                    Add to Home Screen
                  </Button>
                )}
              </CardFooter>
            </Card>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
