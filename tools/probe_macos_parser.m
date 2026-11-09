// MIT: project-authored read-only probe; no Apple implementation is redistributed.
#import <Foundation/Foundation.h>
#import <objc/runtime.h>
@protocol NJDProbe
- (id)initWithPath:(NSString *)path;
- (id)firstRecord;
- (id)nextRecord;
- (int)error;
@end
int main(int argc,const char **argv){ @autoreleasepool {
 NSString *path=@"/System/Library/Input Methods/JapaneseIM-RomajiTyping.app/Contents/PlugIns/JapaneseIM-RomajiTyping.appex/Contents/Resources/Preferences.prefPane";
 NSError *error=nil; NSBundle *bundle=[NSBundle bundleWithPath:path];
 if(![bundle loadAndReturnError:&error]){fprintf(stderr,"bundle unavailable: %s\n",[[error description] UTF8String]);return 1;}
 if(argc!=2){fprintf(stderr,"usage: probe CSV_FILE\n");return 2;}
 {
  NSString *input=[NSString stringWithUTF8String:argv[1]];
  // Only the caller-provided temporary copy is opened; no dictionary manager or preferences object is created.
  id<NJDProbe> parser=(id<NJDProbe>)[[NSClassFromString(@"TextFile") alloc] initWithPath:input];
  NSMutableArray *records=[NSMutableArray array]; id record=[parser firstRecord];
  while(record && records.count<1000000){[records addObject:record];record=[parser nextRecord];}
  NSDictionary *report=@{@"records":records,@"error":@([parser error])};
  NSData *json=[NSJSONSerialization dataWithJSONObject:report options:NSJSONWritingPrettyPrinted error:&error];
  if(!json){fprintf(stderr,"record serialization failed\n");return 3;}
  fwrite(json.bytes,1,json.length,stdout);puts("");
 }
}return 0;}
