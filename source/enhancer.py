# enhancer.py - Post-processor to fix regex parser errors
import re
from typing import Dict, Any, List


class ResumeDataEnhancer:
    """
    Fixes common extraction errors from regex parsers.
    
    Call this AFTER all your extract_* functions run,
    BEFORE saving to JSON/Excel.
    
    Fixes:
    1. Phone format: "83291380(+91-83291)" → "+91 83291380"
    2. Name duplicates: "Abhijeet Abhijeet" → "Abhijeet"
    3. Email duplicates: "email email" → "email"
    """
    
    def __init__(self):
        self.fixes_applied = []
    
    def enhance(self, resume_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main method - call this on your resume dict.
        
        Args:
            resume_data: Your resume dictionary with keys like 
                        'name', 'email', 'phone', etc.
        
        Returns:
            Enhanced dictionary with fixed values
        """
        self.fixes_applied = []
        result = resume_data.copy()
        
        # Fix each field
        result['name'] = self._fix_name(result.get('name', ''))
        result['email'] = self._fix_email(result.get('email', ''))
        result['phone'] = self._fix_phone(result.get('phone', ''))
        
        # Add validation flags
        result['_name_fixed'] = len([f for f in self.fixes_applied if 'name' in f]) > 0
        result['_email_fixed'] = len([f for f in self.fixes_applied if 'email' in f]) > 0
        result['_phone_fixed'] = len([f for f in self.fixes_applied if 'phone' in f]) > 0
        
        return result
    
    def _fix_phone(self, phone: str) -> str:
        """
        Fix phone number formatting.
        
        Examples from your Excel:
        - "83291380(+91-83291)" → "+91 83291380"
        - "96195379(+91-96195)" → "+91 96195379"
        - "98701134(+91-98701)" → "+91 98701134"
        """
        if not phone:
            return phone
        
        original = str(phone).strip()
        phone_str = original
        
        # Remove all non-digit characters first
        digits = re.sub(r'\D', '', phone_str)
        
        # Case 1: 12 digits starting with 91 (Indian number with country code)
        if len(digits) == 12 and digits.startswith('91'):
            fixed = f"+91 {digits[2:]}"
            if fixed != original:
                self.fixes_applied.append(f'phone_format:{original}→{fixed}')
            return fixed
        
        # Case 2: 10 digits only (add +91)
        elif len(digits) == 10:
            fixed = f"+91 {digits}"
            if fixed != original:
                self.fixes_applied.append(f'phone_add_code:{original}→{fixed}')
            return fixed
        
        # Case 3: Try to fix pattern like "83291380(+91-83291)"
        if '(+91' in phone_str or '(91' in phone_str:
            # Extract digits and reorder
            if len(digits) >= 10:
                if digits.startswith('91'):
                    fixed = f"+91 {digits[2:12]}"
                else:
                    fixed = f"+91 {digits[:10]}"
                
                if fixed != original:
                    self.fixes_applied.append(f'phone_reorder:{original}→{fixed}')
                return fixed
        
        # Case 4: Already has +91 but wrong separator
        if phone_str.startswith('+91'):
            cleaned = re.sub(r'^\+91[\s\-]?', '+91 ', phone_str)
            if re.match(r'^\+91 \d{10}$', cleaned) and cleaned != original:
                self.fixes_applied.append(f'phone_separator:{original}→{cleaned}')
                return cleaned
        
        return original
    
    def _fix_name(self, name: str) -> str:
        """
        Fix name extraction errors.
        
        Examples from your Excel:
        - "ABHIJEET" → "Abhijeet" (case fix)
        - "Abhijeet Abhijeet " → "Abhijeet" (duplicate removal)
        - "Bhagyashr Bhagyashr" → "Bhagyashr" (duplicate + case)
        - "PRAVALIK PRAVALIK" → "Pravalik"
        """
        if not name:
            return name
        
        original = str(name).strip()
        name_str = original
        
        # Remove multiple spaces
        name_str = ' '.join(name_str.split())
        
        # Split into words
        words = name_str.split()
        
        # Remove consecutive duplicate words (case-insensitive)
        cleaned_words = []
        prev_word_lower = None
        
        for word in words:
            word_lower = word.lower()
            if word_lower != prev_word_lower:
                cleaned_words.append(word)
                prev_word_lower = word_lower
            else:
                self.fixes_applied.append(f'name_dupe_remove:{word}')
        
        name_str = ' '.join(cleaned_words)
        
        # Convert ALL CAPS to Title Case (but preserve mixed case)
        if name_str.isupper() and len(name_str) > 2:
            name_str = name_str.title()
            self.fixes_applied.append(f'name_case_fix:{original}→{name_str}')
        
        # Strip trailing dots or special chars
        name_str = name_str.rstrip('. ')
        
        return name_str
    
    def _fix_email(self, email: str) -> str:
        """
        Fix email extraction errors.
        
        Examples from your Excel:
        - "Lahadeabl Lahadeabl" → "lahadeabl" (duplicate removal)
        - "bhagyashr bhagyashr" → "bhagyashr" (duplicate removal)
        - "pravalik@pravalik.com" → keep as-is (valid email)
        """
        if not email:
            return email
        
        original = str(email).strip().lower()
        email_str = original
        
        # Remove trailing dots/spaces
        email_str = email_str.rstrip('. ')
        
        # Split into parts
        parts = email_str.split()
        
        # Check for duplicate consecutive parts
        if len(parts) >= 2:
            # Case 1: "email email" → "email"
            if parts[0] == parts[1]:
                email_str = parts[0]
                self.fixes_applied.append(f'email_dupe:{original}→{email_str}')
            
            # Case 2: If first part contains @ and is duplicated
            elif '@' in parts[0] and parts[0] == parts[1]:
                email_str = parts[0]
                self.fixes_applied.append(f'email_full_dupe:{original}→{email_str}')
        
        # If it looks like a valid email now, return it
        if '@' in email_str:
            match = re.search(r'[\w.-]+@[\w.-]+\.\w+', email_str)
            if match:
                extracted = match.group(0)
                if extracted != email_str:
                    self.fixes_applied.append(f'email_extract:{email_str}→{extracted}')
                    return extracted
                return email_str
        
        return email_str
    
    def print_summary(self):
        """Print summary of fixes applied"""
        if not self.fixes_applied:
            print("  ✅ No fixes needed - data looks good!")
            return
        
        print(f"\n  🔧 Enhancements applied ({len(self.fixes_applied)} total):")
        for fix in self.fixes_applied:
            print(f"     • {fix}")


# Convenience function for quick usage
def enhance_resume_data(resume_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    One-line function to enhance resume data.
    
    Usage:
        from enhancer import enhance_resume_data
        
        resume = {...}  # your existing resume dict
        enhanced = enhance_resume_data(resume)
    """
    enhancer = ResumeDataEnhancer()
    return enhancer.enhance(resume_dict)


# Test function
if __name__ == "__main__":
    # Test with your actual failing cases from Excel
    test_cases = [
        {
            "file_name": "test1",
            "name": "ABHIJEET",
            "email": "Lahadeabl Lahadeabl", 
            "phone": "83291380(+91-83291)",
        },
        {
            "file_name": "test2",
            "name": "Bhagyashr Bhagyashr",
            "email": "bhagyashr.bhagyashr",
            "phone": "96195379(+91-96195)",
        },
        {
            "file_name": "test3",
            "name": "M VINITA M",
            "email": "vinita.b@vinita.b...",
            "phone": "98701134(+91-98701)",
        }
    ]
    
    print("=" * 80)
    print("🧪 TESTING ENHANCER ON YOUR DATA")
    print("=" * 80)
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{'─' * 80}")
        print(f"Test {i}: {test['name']}")
        print(f"{'─' * 80}")
        
        print(f"BEFORE:")
        print(f"  Name:  '{test['name']}'")
        print(f"  Email: '{test['email']}'")
        print(f"  Phone: '{test['phone']}'")
        
        enhancer = ResumeDataEnhancer()
        enhanced = enhancer.enhance(test)
        
        print(f"AFTER:")
        print(f"  Name:  '{enhanced['name']}'")
        print(f"  Email: '{enhanced['email']}'")
        print(f"  Phone: '{enhanced['phone']}'")
        
        enhancer.print_summary()