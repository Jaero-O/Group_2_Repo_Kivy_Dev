#!/bin/bash
# MangoFy Raspberry Pi Setup Script
# Run this script once to set up the complete environment

set -e  # Exit on error

echo "=========================================="
echo "MangoFy Raspberry Pi Setup"
echo "=========================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
    echo -e "${RED}Warning: This doesn't appear to be a Raspberry Pi${NC}"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Update system
echo -e "\n${YELLOW}Step 1: Updating system...${NC}"
sudo apt update
sudo apt upgrade -y

# Install system packages
echo -e "\n${YELLOW}Step 2: Installing system packages...${NC}"
sudo apt install -y \
    libcamera-apps \
    python3-libcamera \
    python3-picamera2 \
    python3-pip \
    python3-venv \
    python3-dev \
    git

# Add user to GPIO group
echo -e "\n${YELLOW}Step 3: Adding user to GPIO group...${NC}"
sudo usermod -a -G gpio $USER
echo -e "${GREEN}✓ User added to gpio group (will take effect after logout)${NC}"

# Create virtual environment with system packages
echo -e "\n${YELLOW}Step 4: Creating virtual environment...${NC}"
cd ~/kivy_v1 || { echo -e "${RED}Error: ~/kivy_v1 not found. Clone the repo first!${NC}"; exit 1; }

if [ -d ".venv" ]; then
    echo "Removing existing .venv..."
    rm -rf .venv
fi

python3 -m venv --system-site-packages .venv
source .venv/bin/activate

# Upgrade pip
echo -e "\n${YELLOW}Step 5: Upgrading pip...${NC}"
pip install --upgrade pip

# Install PyTorch (CPU version)
echo -e "\n${YELLOW}Step 6: Installing PyTorch (this may take a while)...${NC}"
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Install other requirements
echo -e "\n${YELLOW}Step 7: Installing Python packages...${NC}"
pip install -r requirements.txt

# Verify installation
echo -e "\n${YELLOW}Step 8: Verifying installation...${NC}"
python3 << 'VERIFY'
import sys
checks = [
    ("RPi.GPIO", lambda: __import__("RPi.GPIO")),
    ("picamera2", lambda: __import__("picamera2")),
    ("libcamera", lambda: __import__("libcamera")),
    ("cv2", lambda: __import__("cv2")),
    ("numpy", lambda: __import__("numpy")),
    ("pandas", lambda: __import__("pandas")),
    ("rembg", lambda: __import__("rembg")),
    ("onnxruntime", lambda: __import__("onnxruntime")),
    ("torch", lambda: __import__("torch")),
    ("torchvision", lambda: __import__("torchvision")),
    ("kivy", lambda: __import__("kivy")),
]

failed = []
for name, imp in checks:
    try:
        imp()
        print(f"✅ {name}")
    except Exception as e:
        print(f"❌ {name}: {e}")
        failed.append(name)

if failed:
    print(f"\n❌ Some dependencies failed: {', '.join(failed)}")
    sys.exit(1)
else:
    print("\n✅ All dependencies installed successfully!")
VERIFY

if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}=========================================="
    echo "✅ Setup Complete!"
    echo "==========================================${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Log out and log back in (for GPIO permissions)"
    echo "2. Activate venv: source ~/kivy_v1/.venv/bin/activate"
    echo "3. Run app: python kivy-lcd-app/main.py"
    echo ""
    echo "For more info, see RASPBERRY_PI_SETUP.md"
else
    echo -e "\n${RED}Setup failed during verification. Check errors above.${NC}"
    exit 1
fi
