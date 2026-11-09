"""Optional macOS-only official-parser comparison. No IME installation or settings changes."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import platform
import plistlib
import subprocess
import tempfile

BUNDLE=Path('/System/Library/Input Methods/JapaneseIM-RomajiTyping.app/Contents/PlugIns/JapaneseIM-RomajiTyping.appex/Contents/Resources/Preferences.prefPane')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,help='generated macOS additional-dictionary file; tested only via a temporary copy')
    parser.add_argument('--report',type=Path,help='write metadata/counts/hashes; no private paths or word contents')
    args=parser.parse_args()
    if platform.system()!='Darwin' or not BUNDLE.exists():raise SystemExit('installed macOS 27 JapaneseIM parser required')
    binary_sha=hashlib.sha256((BUNDLE/'Contents/MacOS/JIMRomajiPreferences').read_bytes()).hexdigest()
    if platform.mac_ver()[0]!='27.0.1' or binary_sha!='21ab1829feeb666d19b27a881b46cde4bc3a74f0a484b3f250e10c4eb54b1da0':
        raise SystemExit('probe is pinned to the reviewed macOS 27.0.1 parser; review a changed implementation first')
    if args.input:raw=args.input.read_bytes()
    else:
        rows=[('かくうじんじゃ','架空 神社','その他の固有名詞'),('かんま','架空,神社','その他の固有名詞'),
              ('くおーと','架空"神社','その他の固有名詞'),('あ'*32,'社'*64,'その他の固有名詞'),('きゅうじ','𠮷神社','その他の固有名詞')]
        stream=io.StringIO(newline='');csv.writer(stream,quoting=csv.QUOTE_ALL,lineterminator='\n').writerows(rows);raw=stream.getvalue().encode()
    expected=[dict(key=a,word=b,publicSpeech=c) for a,b,c in csv.reader(io.StringIO(raw.decode('utf-8'),newline=''),strict=True)]
    with tempfile.TemporaryDirectory(prefix='njd-macos-parser-') as directory:
        temp=Path(directory);source=temp/'source.txt';source.write_bytes(raw)
        executable=temp/'probe'
        subprocess.run(['xcrun','clang','-fobjc-arc','-framework','Foundation','-framework','AppKit','-framework','PreferencePanes',str(Path(__file__).with_name('probe_macos_parser.m')),'-o',str(executable)],check=True)
        result=subprocess.run([str(executable),str(source)],check=True,capture_output=True,text=True)
        observed=json.loads(result.stdout)
        if observed['error']!=0 or observed['records']!=expected:raise SystemExit('official TextFile parser did not preserve all input fields/records')
        if source.read_bytes()!=raw:raise SystemExit('parser changed temporary input bytes')
    info=plistlib.loads((BUNDLE/'Contents/Info.plist').read_bytes())
    report=dict(schema_version=1,method='read-only official installed TextFile parser comparison; temporary input only',
        target_os=platform.mac_ver()[0],os_build=subprocess.run(['sw_vers','-buildVersion'],check=True,capture_output=True,text=True).stdout.strip(),
        bundle_id=info['CFBundleIdentifier'],bundle_version=info['CFBundleVersion'],
        executable_sha256=binary_sha,
        input_sha256=hashlib.sha256(raw).hexdigest(),rows=len(expected),result='all fields and records preserved',actual_ime_import='not_tested')
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
